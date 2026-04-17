# -*- coding: utf-8 -*-

from .common._base import BaseCheck


LSBLK_COMMAND = 'lsblk'
REQUIRED_MOUNTPOINTS = ('/', '/boot', '[SWAP]')
ABNORMAL_MARKERS = ('unknown', 'drive not available')


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def _format_values(self, values):
        return '|'.join(values) if values else '없음'

    def run(self):
        rc, out, err = self._ssh(LSBLK_COMMAND)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'SSH 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='lsblk 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        lines = [line.rstrip() for line in (out or '').splitlines() if line.strip()]
        if len(lines) < 2:
            return self.fail(
                '디스크 정보 없음',
                message='lsblk 결과를 해석할 수 없습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        header = lines[0]
        if 'NAME' not in header or 'TYPE' not in header:
            return self.fail(
                '디스크 정보 파싱 실패',
                message='lsblk 헤더 형식을 해석할 수 없습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        entries = []
        disk_entries = []
        mountpoints_found = set()
        abnormal_lines = []

        for line in lines[1:]:
            parts = line.split()
            if len(parts) < 6:
                continue

            name = parts[0].lstrip('├└─')
            size = parts[3]
            device_type = parts[5]
            mountpoints = parts[6:] if len(parts) > 6 else []
            normalized_mountpoints = [mount.strip() for mount in mountpoints if mount.strip()]

            entry = {
                'name': name,
                'size': size,
                'type': device_type,
                'mountpoints': normalized_mountpoints,
            }
            entries.append(entry)

            if device_type == 'disk':
                disk_entries.append(entry)

            for mount in normalized_mountpoints:
                mountpoints_found.add(mount)

            lower_line = line.lower()
            if any(marker in lower_line for marker in ABNORMAL_MARKERS):
                abnormal_lines.append(line.strip())

        if not entries:
            return self.fail(
                '디스크 정보 파싱 실패',
                message='lsblk 장치 목록을 해석하지 못했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        if not disk_entries:
            return self.fail(
                '물리 디스크 미인식',
                message=(
                    '운영에 필요한 물리 디스크를 찾지 못했습니다. '
                    '임계치 정보: min_physical_disk_count=1, '
                    f'required_mountpoints={self._format_values(REQUIRED_MOUNTPOINTS)}, '
                    f'abnormal_markers={self._format_values(ABNORMAL_MARKERS)}. '
                    '판단근거: lsblk 결과에서 TYPE=disk 항목이 0개입니다.'
                ),
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        missing_mountpoints = [
            mountpoint for mountpoint in REQUIRED_MOUNTPOINTS
            if mountpoint not in mountpoints_found
        ]

        if abnormal_lines:
            return self.fail(
                '디스크 인식 상태 비정상',
                message=(
                    '비정상 디스크 상태가 확인되었습니다. '
                    f'임계치 정보: abnormal_markers={self._format_values(ABNORMAL_MARKERS)}. '
                    '판단근거: 다음 lsblk 라인에서 비정상 마커가 확인되었습니다: '
                    + '; '.join(abnormal_lines)
                ),
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        if missing_mountpoints:
            return self.fail(
                '필수 마운트 누락',
                message=(
                    '필수 마운트가 확인되지 않습니다: ' + ', '.join(missing_mountpoints) + '. '
                    f'임계치 정보: required_mountpoints={self._format_values(REQUIRED_MOUNTPOINTS)}. '
                    f'판단근거: 확인된 마운트={self._format_values(sorted(mountpoints_found))}, '
                    f'누락된 마운트={self._format_values(missing_mountpoints)}.'
                ),
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        return self.ok(
            metrics={
                'block_device_count': len(entries),
                'physical_disk_count': len(disk_entries),
                'physical_disks': [entry['name'] for entry in disk_entries],
                'mountpoints_found': sorted(mountpoints_found),
                'abnormal_lines': abnormal_lines,
                'devices': entries,
            },
            thresholds={
                'min_physical_disk_count': 1,
                'required_mountpoints': self._format_values(REQUIRED_MOUNTPOINTS),
                'abnormal_markers': self._format_values(ABNORMAL_MARKERS),
            },
            reasons=(
                f'물리 디스크 {len(disk_entries)}개가 인식되었고 '
                f'필수 마운트({self._format_values(REQUIRED_MOUNTPOINTS)})가 모두 확인되었으며 '
                '비정상 마커가 검출되지 않았습니다.'
            ),
            message=(
                'lsblk 기준 디스크 인식 점검이 정상 수행되었습니다. '
                '임계치 정보: min_physical_disk_count=1, '
                f'required_mountpoints={self._format_values(REQUIRED_MOUNTPOINTS)}, '
                f'abnormal_markers={self._format_values(ABNORMAL_MARKERS)}. '
                f'판단기준: 물리 디스크가 1개 이상이고 필수 마운트가 모두 존재하며 '
                '비정상 마커가 없어야 합니다. '
                f'판단근거: physical_disk_count={len(disk_entries)}, '
                f'mountpoints_found={self._format_values(sorted(mountpoints_found))}, '
                'abnormal_line_count=0.'
            ),
        )


CHECK_CLASS = Check
