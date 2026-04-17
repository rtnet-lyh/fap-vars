# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


DISK_MOUNT_COMMAND = (
    "$d=Get-Disk -ErrorAction SilentlyContinue; "
    "@(@($d|ForEach-Object{[pscustomobject]@{NAME=\"Disk$($_.Number)\";RM=[int]($_.BusType -in @('USB','SD','MMC')); 'SIZE(GB)'=[math]::Round($_.Size/1GB,2);RO=[int]$_.IsReadOnly;TYPE='disk';MOUNTPOINT='';STATUS=(@($_.OperationalStatus)-join ',')}}) + "
    "@((Get-Partition -ErrorAction SilentlyContinue)|ForEach-Object{$n=$_.DiskNumber; $dk=$d|Where-Object Number -eq $n; [pscustomobject]@{NAME=\"Disk$($_.DiskNumber)-Part$($_.PartitionNumber)\";RM=[int]($dk.BusType -in @('USB','SD','MMC')); 'SIZE(GB)'=[math]::Round($_.Size/1GB,2);RO=[int]$_.IsReadOnly;TYPE='part';MOUNTPOINT=(($_.AccessPaths|Where-Object{$_})-join ',').TrimEnd('\\');STATUS=(@($dk.OperationalStatus)-join ',')}}) + "
    "@((Get-CimInstance Win32_CDROMDrive -ErrorAction SilentlyContinue)|ForEach-Object{[pscustomobject]@{NAME=$(if($_.Drive){$_.Drive}else{$_.Caption});RM=1;'SIZE(GB)'=$(if($_.Size){[math]::Round([double]$_.Size/1GB,2)}else{$null});RO=1;TYPE='rom';MOUNTPOINT=$_.Drive;STATUS=$(if($_.MediaLoaded){$_.Status}else{'No Media'})}})) | "
    "Format-Table -Auto"
)


def _parse_float(value):
    return round(float(str(value).strip()), 2)


def _parse_int(value):
    return int(str(value).strip())


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
            return self.not_applicable(
                'WinRM 실행 환경을 사용할 수 없습니다.',
                raw_output=(err or '').strip(),
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
                message='디스크 마운트 상태 결과에서 실패 키워드가 확인되었습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        lines = [line.rstrip() for line in text.splitlines() if line.strip()]
        if len(lines) < 3:
            return self.fail(
                '디스크 마운트 정보 없음',
                message='디스크 마운트 상태 결과를 해석할 수 없습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        parsed = []
        row_pattern = re.compile(
            r'^(?P<name>\S+)\s+'
            r'(?P<rm>[01])\s+'
            r'(?P<size>[0-9]+(?:\.[0-9]+)?)\s+'
            r'(?P<ro>[01])\s+'
            r'(?P<type>disk|part|rom)\s+'
            r'(?P<mountpoint>.*?)\s+'
            r'(?P<status>\S.*)$'
        )

        for line in lines[2:]:
            if line.lstrip().startswith('---'):
                continue

            match = row_pattern.match(line)
            if not match:
                continue

            parsed.append({
                'name': match.group('name'),
                'rm': _parse_int(match.group('rm')),
                'size_gb': _parse_float(match.group('size')),
                'ro': _parse_int(match.group('ro')),
                'type': match.group('type'),
                'mountpoint': match.group('mountpoint').strip(),
                'status': match.group('status').strip(),
            })

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
            message='Windows 디스크 마운트 상태 점검이 정상 수행되었습니다.',
        )


CHECK_CLASS = Check
