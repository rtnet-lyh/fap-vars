# type_name

일상점검

# area_name

상태점검

# category_name

server

# application_type

linux

# application

rocky

# inspection_code

U-REPLAY-LSBLK-01

# is_required

권고

# inspection_name

Disk 인식여부 점검

# inspection_content

Disk 인식 정상 유무 점검(Disk Status : Unknown/Drive not available)

# inspection_command

```bash
lsblk
```

# inspection_output

```text
NAME          MAJ:MIN RM  SIZE RO TYPE MOUNTPOINTS
sda             8:0    0   50G  0 disk
├─sda1          8:1    0    1G  0 part /boot
└─sda2          8:2    0   49G  0 part
  ├─rhel-root 253:0    0 45.1G  0 lvm  /
  └─rhel-swap 253:1    0  3.9G  0 lvm  [SWAP]
sr0            11:0    1  1.3G  0 rom
```

# description

본 항목은 `lsblk` 명령 결과를 기준으로 시스템에 연결된 블록 디바이스가 정상적으로 인식되는지 점검한다.
점검 시 물리 디스크(`disk`), 파티션(`part`), LVM/RAID 등 논리 디바이스의 계층 구조와 크기, 마운트 정보를 함께 확인한다.
운영에 필요한 주요 디스크와 파티션이 정상적으로 표시되고 루트(`/`), 부트(`/boot`), 스왑(`[SWAP]`) 등 필수 마운트가 기대한 형태로 보이면 양호로 판단한다.
반대로 디스크가 비정상적으로 누락되거나 용량 정보가 비정상적이거나 필요한 마운트 구성이 확인되지 않으면 디스크 인식 이상 또는 스토리지 구성 문제 가능성이 있으므로 주의가 필요하다.

`lsblk` 결과에서 운영에 필요한 물리 디스크가 정상적으로 표시되고, 주요 파티션 및 논리 볼륨이 계층 구조에 맞게 인식되며
루트(`/`), 부트(`/boot`), 스왑(`[SWAP]`) 등 필수 파일시스템 또는 논리 볼륨이 정상적으로 확인되면 양호로 판단한다.

필요한 물리 디스크가 보이지 않거나, 파티션 또는 논리 볼륨 구성이 누락되어 있거나,
용량이 비정상적으로 표시되거나, 필수 마운트 지점이 확인되지 않으면 불량으로 판단한다.

광학 장치(`rom`)나 이동식 장치처럼 운영 필수 디스크가 아닌 장치는 환경에 따라 없을 수 있으므로
시스템 운영에 필요한 디스크 인식 여부를 중심으로 판단한다.

# thresholds

[
    {id: null, key: "본 항목은 수치 임계치 기반 점검이 아니며, 디스크/파티션/마운트 인식 상태를 기준으로 판단한다.", value: "", sortOrder: 0}
]

# inspection_script

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
