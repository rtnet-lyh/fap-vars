# -*- coding: utf-8 -*-

from .common._base import BaseCheck


DISK_IO_SPLIT_MARKER = '__DISKSTATS_SPLIT__'
DISK_IO_COMMAND = (
    "bash -lc '"
    "cat /proc/diskstats; "
    "printf \"{marker}\\n\"; "
    "sleep 1; "
    "cat /proc/diskstats"
    "'"
).format(marker=DISK_IO_SPLIT_MARKER)


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def _parse_snapshot(self, lines):
        entries = {}

        for raw_line in lines:
            parts = raw_line.split()
            if len(parts) < 14:
                raise ValueError(f'invalid diskstats line: {raw_line}')

            name = parts[2]
            try:
                entries[name] = {
                    'reads_completed': int(parts[3]),
                    'sectors_read': int(parts[5]),
                    'writes_completed': int(parts[7]),
                    'sectors_written': int(parts[9]),
                    'io_time_ms': int(parts[12]),
                    'weighted_io_time_ms': int(parts[13]),
                }
            except ValueError as exc:
                raise ValueError(f'invalid diskstats value: {raw_line}') from exc

        if not entries:
            raise ValueError('empty diskstats snapshot')

        return entries

    def run(self):
        read_write_increase_trend = self.get_threshold_var('read_write_increase_trend', default=100.0, value_type='float')
        io_time_increase_trend = self.get_threshold_var('io_time_increase_trend', default=100.0, value_type='float')
        rc, out, err = self._ssh(DISK_IO_COMMAND)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'SSH 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='디스크 I/O 점검 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        lines = [line.strip() for line in (out or '').splitlines() if line.strip()]
        marker_indexes = [
            index for index, line in enumerate(lines)
            if line == DISK_IO_SPLIT_MARKER
        ]
        if len(marker_indexes) != 1:
            return self.fail(
                '디스크 통계 파싱 실패',
                message='2회 수집된 /proc/diskstats 결과에서 구분자를 정확히 1회 찾지 못했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        marker_index = marker_indexes[0]
        before_lines = lines[:marker_index]
        after_lines = lines[marker_index + 1:]
        if not before_lines or not after_lines:
            return self.fail(
                '디스크 통계 파싱 실패',
                message='구분자 전후의 /proc/diskstats 스냅샷이 모두 존재해야 합니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        try:
            before_stats = self._parse_snapshot(before_lines)
            after_stats = self._parse_snapshot(after_lines)
        except ValueError as exc:
            return self.fail(
                '디스크 통계 파싱 실패',
                message=str(exc),
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        device_names = sorted(set(before_stats) & set(after_stats))
        if not device_names:
            return self.fail(
                '디스크 통계 비교 실패',
                message='전후 스냅샷 간 공통 디스크 장치를 찾지 못했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        device_deltas = []
        overloaded_devices = []

        for name in device_names:
            before = before_stats[name]
            after = after_stats[name]
            read_requests_delta = after['reads_completed'] - before['reads_completed']
            write_requests_delta = after['writes_completed'] - before['writes_completed']
            read_write_delta = read_requests_delta + write_requests_delta
            read_sectors_delta = after['sectors_read'] - before['sectors_read']
            write_sectors_delta = after['sectors_written'] - before['sectors_written']
            sectors_delta = read_sectors_delta + write_sectors_delta
            io_time_delta_ms = after['io_time_ms'] - before['io_time_ms']
            weighted_io_time_delta_ms = after['weighted_io_time_ms'] - before['weighted_io_time_ms']

            entry = {
                'device_name': name,
                'read_requests_delta': read_requests_delta,
                'write_requests_delta': write_requests_delta,
                'read_write_delta': read_write_delta,
                'read_sectors_delta': read_sectors_delta,
                'write_sectors_delta': write_sectors_delta,
                'sectors_delta': sectors_delta,
                'io_time_delta_ms': io_time_delta_ms,
                'weighted_io_time_delta_ms': weighted_io_time_delta_ms,
            }
            device_deltas.append(entry)

            if read_write_delta > read_write_increase_trend or io_time_delta_ms > io_time_increase_trend:
                overloaded_devices.append(
                    f"{name}(rw_delta={read_write_delta}, io_ms_delta={io_time_delta_ms})"
                )

        device_deltas.sort(
            key=lambda entry: (
                entry['read_write_delta'],
                entry['io_time_delta_ms'],
                entry['weighted_io_time_delta_ms'],
                entry['sectors_delta'],
            ),
            reverse=True,
        )

        top_read_write = max(device_deltas, key=lambda entry: entry['read_write_delta'])
        top_io_time = max(device_deltas, key=lambda entry: entry['io_time_delta_ms'])

        if overloaded_devices:
            return self.fail(
                '디스크 I/O 증가 추세 감지',
                message='일부 디스크에서 I/O 증가 추세가 임계치를 초과했습니다: ' + ', '.join(overloaded_devices),
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        return self.ok(
            metrics={
                'snapshot_line_count': len(lines),
                'device_count': len(device_deltas),
                'max_read_write_delta': top_read_write['read_write_delta'],
                'max_read_write_target': top_read_write['device_name'],
                'max_io_time_delta_ms': top_io_time['io_time_delta_ms'],
                'max_io_time_target': top_io_time['device_name'],
                'device_deltas': device_deltas,
            },
            thresholds={
                'read_write_increase_trend': read_write_increase_trend,
                'io_time_increase_trend': io_time_increase_trend,
            },
            reasons='1초 간격 전후 비교에서 과도한 read/write 증가나 I/O 처리 시간 증가가 확인되지 않았습니다.',
            message=(
                '디스크 I/O 상태 점검이 정상 수행되었습니다. '
                f"max_rw_delta={top_read_write['read_write_delta']}({top_read_write['device_name']}), "
                f"max_io_ms_delta={top_io_time['io_time_delta_ms']}({top_io_time['device_name']})"
            ),
        )


CHECK_CLASS = Check
