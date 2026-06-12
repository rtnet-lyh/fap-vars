# type_name

일상점검

# area_name

상태점검

# category_name

server

# application_type

windows

# application

windows2019

# inspection_code

W-REPLAY-DISK-MOUNT-01

# is_required

필수

# inspection_name

# inspection_content

Get-Disk와 Get-Partition 결과를 이용해 디스크 수와 파티션 수가 최소 기준을 만족하는지 확인합니다.

# inspection_command

```bash
$OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); $d=Get-Disk -ErrorAction SilentlyContinue; @(@($d|ForEach-Object{[pscustomobject]@{NAME="Disk$($_.Number)";RM=[int]($_.BusType -in @('USB','SD','MMC')); 'SIZE(GB)'=[math]::Round($_.Size/1GB,2);RO=[int]$_.IsReadOnly;TYPE='disk';MOUNTPOINT='';STATUS=(@($_.OperationalStatus)-join ',')}}) + @((Get-Partition -ErrorAction SilentlyContinue)|ForEach-Object{$n=$_.DiskNumber; $dk=$d|Where-Object Number -eq $n; [pscustomobject]@{NAME="Disk$($_.DiskNumber)-Part$($_.PartitionNumber)";RM=[int]($dk.BusType -in @('USB','SD','MMC')); 'SIZE(GB)'=[math]::Round($_.Size/1GB,2);RO=[int]$_.IsReadOnly;TYPE='part';MOUNTPOINT=(($_.AccessPaths|Where-Object{$_})-join ',').TrimEnd('\');STATUS=(@($dk.OperationalStatus)-join ',')}}) + @((Get-CimInstance Win32_CDROMDrive -ErrorAction SilentlyContinue)|ForEach-Object{[pscustomobject]@{NAME=$(if($_.Drive){$_.Drive}else{$_.Caption});RM=1;'SIZE(GB)'=$(if($_.Size){[math]::Round([double]$_.Size/1GB,2)}else{$null});RO=1;TYPE='rom';MOUNTPOINT=$_.Drive;STATUS=$(if($_.MediaLoaded){$_.Status}else{'No Media'})}})) | ConvertTo-Json -Depth 3
```

# inspection_output

```text
[
  {
    "NAME": "Disk0",
    "RM": 0,
    "SIZE(GB)": 476.94,
    "RO": 0,
    "TYPE": "disk",
    "MOUNTPOINT": "",
    "STATUS": "Online"
  },
  {
    "NAME": "Disk0-Part1",
    "RM": 0,
    "SIZE(GB)": 476.34,
    "RO": 0,
    "TYPE": "part",
    "MOUNTPOINT": "C:",
    "STATUS": "Online"
  }
]
```

# description

- 스토리지 장치가 OS에 인식되는지와 실제 파티션이 구성되어 있는지를 함께 점검합니다.
- 최소 디스크 수와 최소 파티션 수를 기준으로 기본 스토리지 구성을 검증합니다.

- **정상**: 디스크 수와 파티션 수가 모두 최소 기준 이상입니다.
- **경고**: 디스크 미인식, 파티션 누락 등으로 기준 미달입니다.

# thresholds

[
    {id: null, key: "min_disk_count", value: "1", sortOrder: 0}
,
{id: null, key: "min_partition_count", value: "1", sortOrder: 1}
,
{id: null, key: "failure_keywords", value: "", sortOrder: 2}
]

# inspection_script

# -*- coding: utf-8 -*-

import json

from .common._base import BaseCheck


DISK_MOUNT_COMMAND = (
    "$OutputEncoding = [System.Text.UTF8Encoding]::new($false); "
    "[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); "
    "$d=Get-Disk -ErrorAction SilentlyContinue; "
    "@(@($d|ForEach-Object{[pscustomobject]@{NAME=\"Disk$($_.Number)\";RM=[int]($_.BusType -in @('USB','SD','MMC')); 'SIZE(GB)'=[math]::Round($_.Size/1GB,2);RO=[int]$_.IsReadOnly;TYPE='disk';MOUNTPOINT='';STATUS=(@($_.OperationalStatus)-join ',')}}) + "
    "@((Get-Partition -ErrorAction SilentlyContinue)|ForEach-Object{$n=$_.DiskNumber; $dk=$d|Where-Object Number -eq $n; [pscustomobject]@{NAME=\"Disk$($_.DiskNumber)-Part$($_.PartitionNumber)\";RM=[int]($dk.BusType -in @('USB','SD','MMC')); 'SIZE(GB)'=[math]::Round($_.Size/1GB,2);RO=[int]$_.IsReadOnly;TYPE='part';MOUNTPOINT=(($_.AccessPaths|Where-Object{$_})-join ',').TrimEnd('\\');STATUS=(@($dk.OperationalStatus)-join ',')}}) + "
    "@((Get-CimInstance Win32_CDROMDrive -ErrorAction SilentlyContinue)|ForEach-Object{[pscustomobject]@{NAME=$(if($_.Drive){$_.Drive}else{$_.Caption});RM=1;'SIZE(GB)'=$(if($_.Size){[math]::Round([double]$_.Size/1GB,2)}else{$null});RO=1;TYPE='rom';MOUNTPOINT=$_.Drive;STATUS=$(if($_.MediaLoaded){$_.Status}else{'No Media'})}})) | "
    "ConvertTo-Json -Depth 3"
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
        min_disk_count = self.get_threshold_var('min_disk_count', default=1, value_type='int')
        min_partition_count = self.get_threshold_var('min_partition_count', default=1, value_type='int')
        failure_keywords_raw = self.get_threshold_var('failure_keywords', default='', value_type='str')

        rc, out, err = self._run_ps(DISK_MOUNT_COMMAND)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'WinRM 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if self._is_not_applicable(rc, err):
            return self.fail(
                'WinRM 실행 환경을 사용할 수 없습니다.',
                message='Windows 디스크 마운트 상태 점검을 수행할 수 없습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='Windows 디스크 마운트 상태 점검 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        text = (out or '').strip()
        if not text:
            return self.fail(
                '디스크 마운트 정보 없음',
                message='디스크 마운트 상태 결과가 비어 있습니다.',
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
                '디스크 마운트 실패 키워드 감지',
                message=f'디스크 마운트 상태 결과에서 실패 키워드가 확인되었습니다: {json.dumps(matched_failure_keywords)}',
                stdout=text,
                stderr=(err or '').strip(),
            )

        try:
            raw_entries = json.loads(text)
        except json.JSONDecodeError:
            return self.fail(
                '디스크 마운트 파싱 실패',
                message='디스크/파티션/ROM 장치 JSON을 해석하지 못했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        parsed = []
        for entry in _as_list(raw_entries):
            if not isinstance(entry, dict):
                continue
            try:
                parsed.append({
                    'name': str(entry.get('NAME', '')).strip(),
                    'rm': _parse_int(entry.get('RM', 0)),
                    'size_gb': _parse_float(entry.get('SIZE(GB)', 0)),
                    'ro': _parse_int(entry.get('RO', 0)),
                    'type': str(entry.get('TYPE', '')).strip(),
                    'mountpoint': str(entry.get('MOUNTPOINT', '')).strip(),
                    'status': str(entry.get('STATUS', '')).strip(),
                })
            except (TypeError, ValueError):
                continue

        if not parsed:
            return self.fail(
                '디스크 마운트 파싱 실패',
                message='디스크/파티션/ROM 장치 정보를 해석하지 못했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        disk_entries = [entry for entry in parsed if entry['type'] == 'disk']
        partition_entries = [entry for entry in parsed if entry['type'] == 'part']
        rom_entries = [entry for entry in parsed if entry['type'] == 'rom']

        if len(disk_entries) < min_disk_count:
            return self.fail(
                '디스크 인식 수 기준 미달',
                message='인식된 디스크 수가 기준치 미만입니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        if len(partition_entries) < min_partition_count:
            return self.fail(
                '파티션 인식 수 기준 미달',
                message='인식된 파티션 수가 기준치 미만입니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        offline_entries = [
            entry['name']
            for entry in parsed
            if entry['type'] in ('disk', 'part') and 'online' not in entry['status'].lower()
        ]
        read_only_disk_entries = [
            entry['name']
            for entry in parsed
            if entry['type'] in ('disk', 'part') and entry['ro'] != 0
        ]

        if offline_entries:
            return self.fail(
                '오프라인 디스크 장치 감지',
                message='Online 상태가 아닌 디스크 또는 파티션이 확인되었습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        if read_only_disk_entries:
            return self.fail(
                '읽기 전용 디스크 장치 감지',
                message='읽기 전용으로 표시된 디스크 또는 파티션이 확인되었습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        mounted_partition_count = len([entry for entry in partition_entries if entry['mountpoint']])
        largest_disk = max(disk_entries, key=lambda entry: entry['size_gb'])

        return self.ok(
            metrics={
                'device_count': len(parsed),
                'disk_count': len(disk_entries),
                'partition_count': len(partition_entries),
                'rom_count': len(rom_entries),
                'mounted_partition_count': mounted_partition_count,
                'largest_disk_name': largest_disk['name'],
                'largest_disk_size_gb': largest_disk['size_gb'],
                'offline_entries': offline_entries,
                'read_only_disk_entries': read_only_disk_entries,
                'disk_names': [entry['name'] for entry in disk_entries],
                'partition_names': [entry['name'] for entry in partition_entries],
                'rom_names': [entry['name'] for entry in rom_entries],
                'matched_failure_keywords': matched_failure_keywords,
            },
            thresholds={
                'min_disk_count': min_disk_count,
                'min_partition_count': min_partition_count,
                'failure_keywords': failure_keywords,
            },
            reasons='디스크, 파티션, 마운트 상태가 모두 기준 범위 내입니다.',
            message=(
                f'Windows 디스크 마운트 상태 점검이 정상입니다. 현재 상태: '
                f'디스크 {len(disk_entries)}개 (기준 {min_disk_count}개 이상), '
                f'파티션 {len(partition_entries)}개 (기준 {min_partition_count}개 이상), '
                f'마운트된 파티션 {mounted_partition_count}개, 최대 디스크 {largest_disk["name"]} '
                f'{largest_disk["size_gb"]:.2f}GB.'
            ),
        )


CHECK_CLASS = Check
