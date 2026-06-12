# -*- coding: utf-8 -*-

import json

from .common._base import BaseCheck


DISK_IO_COMMAND = (
    "$OutputEncoding = [System.Text.UTF8Encoding]::new($false); "
    "[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); "
    "Get-CimInstance Win32_PerfFormattedData_PerfDisk_PhysicalDisk | "
    "Where-Object { $_.Name -ne '_Total' } | "
    "Select-Object @{N='device';E={$_.Name}},@{N='r/s';E={$_.DiskReadsPerSec}},@{N='w/s';E={$_.DiskWritesPerSec}},"
    "@{N='kr/s';E={[math]::Round($_.DiskReadBytesPerSec/1KB,2)}},@{N='kw/s';E={[math]::Round($_.DiskWriteBytesPerSec/1KB,2)}},"
    "@{N='wait(ms)';E={[math]::Round($_.AvgDiskSecPerTransfer*1000,2)}},@{N='actv';E={[math]::Round($_.AvgDiskQueueLength,2)}},"
    "@{N='%b';E={[math]::Round($_.PercentDiskTime,2)}},@{N='idle%';E={[math]::Round($_.PercentIdleTime,2)}} | ConvertTo-Json -Depth 3"
)


def _parse_float(value):
    return round(float(str(value).strip()), 2)


def _parse_int(value):
    return int(str(value).strip())


def _as_list(value):
    if isinstance(value, list):
        return value
    if value in (None, ''):
        return []
    return [value]


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'winrm'
    WINRM_SHELL = 'powershell'

    def run(self):
        max_busy_percent = self.get_threshold_var('max_busy_percent', default=80.0, value_type='float')
        min_idle_percent = self.get_threshold_var('min_idle_percent', default=20.0, value_type='float')
        max_wait_ms = self.get_threshold_var('max_wait_ms', default=10.0, value_type='float')
        max_queue_length = self.get_threshold_var('max_queue_length', default=1.0, value_type='float')
        failure_keywords_raw = self.get_threshold_var('failure_keywords', default='', value_type='str')

        rc, out, err = self._run_ps(DISK_IO_COMMAND)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'WinRM 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if self._is_not_applicable(rc, err):
            return self.fail(
                'WinRM 실행 환경을 사용할 수 없습니다.',
                message='Windows 디스크 I/O 점검을 수행할 수 없습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='Windows 디스크 I/O 점검 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        text = (out or '').strip()
        if not text:
            return self.fail(
                '디스크 I/O 정보 없음',
                message='디스크 I/O 결과가 비어 있습니다.',
                stdout='',
                stderr=(err or '').strip(),
            )

        failure_keywords = [
            keyword.strip()
            for keyword in failure_keywords_raw.split(',')
            if keyword.strip()
        ]
        matched_failure_keywords = [
            keyword for keyword in failure_keywords if keyword.lower() in text.lower()
        ]
        if matched_failure_keywords:
            return self.fail(
                '디스크 I/O 실패 키워드 감지',
                message='디스크 I/O 결과에서 실패 키워드가 확인되었습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        try:
            raw_entries = json.loads(text)
        except json.JSONDecodeError:
            return self.fail(
                '디스크 I/O 파싱 실패',
                message='디스크 I/O 장치 JSON을 해석하지 못했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        parsed = []
        for entry in _as_list(raw_entries):
            if not isinstance(entry, dict):
                continue
            try:
                parsed.append({
                    'device': str(entry.get('device', '')).strip(),
                    'reads_per_sec': _parse_int(entry.get('r/s', 0)),
                    'writes_per_sec': _parse_int(entry.get('w/s', 0)),
                    'read_kb_per_sec': _parse_float(entry.get('kr/s', 0)),
                    'write_kb_per_sec': _parse_float(entry.get('kw/s', 0)),
                    'wait_ms': _parse_float(entry.get('wait(ms)', 0)),
                    'queue_length': _parse_float(entry.get('actv', 0)),
                    'busy_percent': _parse_float(entry.get('%b', 0)),
                    'idle_percent': _parse_float(entry.get('idle%', 0)),
                })
            except (TypeError, ValueError):
                continue

        if not parsed:
            return self.fail(
                '디스크 I/O 파싱 실패',
                message='디스크 I/O 장치 정보를 해석하지 못했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        busiest_device = max(parsed, key=lambda entry: entry['busy_percent'])
        slowest_device = max(parsed, key=lambda entry: entry['wait_ms'])
        longest_queue_device = max(parsed, key=lambda entry: entry['queue_length'])

        over_busy_devices = [
            f"{entry['device']}({entry['busy_percent']}%)"
            for entry in parsed
            if entry['busy_percent'] >= max_busy_percent
        ]
        low_idle_devices = [
            f"{entry['device']}({entry['idle_percent']}%)"
            for entry in parsed
            if entry['idle_percent'] <= min_idle_percent
        ]
        high_wait_devices = [
            f"{entry['device']}({entry['wait_ms']}ms)"
            for entry in parsed
            if entry['wait_ms'] > max_wait_ms
        ]
        long_queue_devices = [
            f"{entry['device']}({entry['queue_length']})"
            for entry in parsed
            if entry['queue_length'] > max_queue_length
        ]

        if over_busy_devices:
            return self.fail(
                '디스크 Busy 비율 임계치 초과',
                message='일부 디스크 Busy 비율이 기준치를 초과했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        if low_idle_devices:
            return self.fail(
                '디스크 Idle 비율 임계치 미달',
                message='일부 디스크 Idle 비율이 기준치 이하입니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        if high_wait_devices:
            return self.fail(
                '디스크 대기시간 임계치 초과',
                message='일부 디스크 평균 대기시간이 기준치를 초과했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        if long_queue_devices:
            return self.fail(
                '디스크 큐 길이 임계치 초과',
                message='일부 디스크 큐 길이가 기준치를 초과했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        return self.ok(
            metrics={
                'device_count': len(parsed),
                'busiest_device': busiest_device['device'],
                'max_busy_percent': busiest_device['busy_percent'],
                'slowest_device': slowest_device['device'],
                'max_wait_ms': slowest_device['wait_ms'],
                'longest_queue_device': longest_queue_device['device'],
                'max_queue_length': longest_queue_device['queue_length'],
                'max_read_kb_per_sec': max(entry['read_kb_per_sec'] for entry in parsed),
                'max_write_kb_per_sec': max(entry['write_kb_per_sec'] for entry in parsed),
                'over_busy_devices': over_busy_devices,
                'low_idle_devices': low_idle_devices,
                'high_wait_devices': high_wait_devices,
                'long_queue_devices': long_queue_devices,
                'matched_failure_keywords': matched_failure_keywords,
            },
            thresholds={
                'max_busy_percent': max_busy_percent,
                'min_idle_percent': min_idle_percent,
                'max_wait_ms': max_wait_ms,
                'max_queue_length': max_queue_length,
                'failure_keywords': failure_keywords,
            },
            reasons='디스크 Busy 비율, Idle 비율, 대기시간, 큐 길이가 모두 기준 범위 내입니다.',
            message=(
                f'Windows 디스크 I/O 점검이 정상입니다. 현재 상태: '
                f'장치 {len(parsed)}개, 최고 Busy {busiest_device["device"]} '
                f'{busiest_device["busy_percent"]:.2f}% (기준 {max_busy_percent:.2f}% 미만), '
                f'최대 대기시간 {slowest_device["device"]} {slowest_device["wait_ms"]:.2f}ms '
                f'(기준 {max_wait_ms:.2f}ms 이하), 최대 큐 길이 {longest_queue_device["device"]} '
                f'{longest_queue_device["queue_length"]:.2f} (기준 {max_queue_length:.2f} 이하).'
            ),
        )


CHECK_CLASS = Check
