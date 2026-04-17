# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


DISK_HA_COMMAND = (
    "Get-Disk | ForEach-Object { $d=$_; $vd=Get-VirtualDisk -Disk $d -ErrorAction SilentlyContinue; "
    "if($vd){ $pd=$vd | Get-PhysicalDisk -ErrorAction SilentlyContinue; "
    "\"Disk $($d.Number) [$($d.FriendlyName)] : Storage Spaces RAID device / State=$((@($vd.OperationalStatus) | Sort-Object -Unique) -join ',') / Health=$($vd.HealthStatus) / RaidDevices=$($pd.Count) / ActiveDevices=$(($pd | Where-Object {$_.OperationalStatus -eq 'OK'} | Measure-Object).Count) / WorkingDevices=$(($pd | Where-Object {$_.HealthStatus -eq 'Healthy'} | Measure-Object).Count) / FailedDevices=$(($pd | Where-Object {$_.OperationalStatus -ne 'OK' -or $_.HealthStatus -ne 'Healthy'} | Measure-Object).Count) / SpareDevices=$(try{(($vd | Get-StoragePool | Get-PhysicalDisk | Where-Object {$_.Usage -eq 'HotSpare'} | Measure-Object).Count)}catch{0})\" "
    "} else { \"Disk $($d.Number) [$($d.FriendlyName)] : does not appear to be a Storage Spaces RAID device\" } }"
)


def _parse_int(value):
    return int(str(value).strip())


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'winrm'
    WINRM_SHELL = 'powershell'

    def run(self):
        require_spare_device = self.get_threshold_var('require_spare_device', default=0, value_type='int')
        failure_keywords_raw = self.get_threshold_var('failure_keywords', default='', value_type='str')

        rc, out, err = self._run_ps(DISK_HA_COMMAND)

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
                message='Windows 디스크 HA 점검 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        text = (out or '').strip()
        if not text:
            return self.fail(
                '디스크 HA 정보 없음',
                message='디스크 HA 점검 결과가 비어 있습니다.',
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
                '디스크 HA 실패 키워드 감지',
                message='디스크 HA 결과에서 실패 키워드가 확인되었습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        non_raid_marker = 'does not appear to be a Storage Spaces RAID device'
        raid_marker = 'Storage Spaces RAID device / State='
        non_raid_lines = [line for line in lines if non_raid_marker in line]
        raid_lines = [line for line in lines if raid_marker in line]

        if not raid_lines:
            return self.not_applicable(
                'Storage Spaces RAID 장치를 찾지 못했습니다.',
                raw_output=text,
            )

        parsed = []
        pattern = re.compile(
            r'^Disk (?P<number>\d+) \[(?P<name>.*?)\] : Storage Spaces RAID device / '
            r'State=(?P<state>.*?) / Health=(?P<health>.*?) / '
            r'RaidDevices=(?P<raid>\d+) / ActiveDevices=(?P<active>\d+) / '
            r'WorkingDevices=(?P<working>\d+) / FailedDevices=(?P<failed>\d+) / SpareDevices=(?P<spare>\d+)$'
        )

        for line in raid_lines:
            match = pattern.match(line)
            if not match:
                continue

            parsed.append({
                'disk_number': _parse_int(match.group('number')),
                'friendly_name': match.group('name').strip(),
                'state': match.group('state').strip(),
                'health': match.group('health').strip(),
                'raid_devices': _parse_int(match.group('raid')),
                'active_devices': _parse_int(match.group('active')),
                'working_devices': _parse_int(match.group('working')),
                'failed_devices': _parse_int(match.group('failed')),
                'spare_devices': _parse_int(match.group('spare')),
            })

        if not parsed:
            return self.fail(
                '디스크 HA 정보 파싱 실패',
                message='Storage Spaces RAID 상태 정보를 해석하지 못했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        degraded_disks = [
            f"Disk {entry['disk_number']}({entry['state']})"
            for entry in parsed
            if entry['state'].lower() != 'ok'
        ]
        unhealthy_disks = [
            f"Disk {entry['disk_number']}({entry['health']})"
            for entry in parsed
            if entry['health'].lower() != 'healthy'
        ]
        failed_device_disks = [
            f"Disk {entry['disk_number']}({entry['failed_devices']})"
            for entry in parsed
            if entry['failed_devices'] > 0
        ]
        inactive_device_disks = [
            f"Disk {entry['disk_number']}(raid={entry['raid_devices']},active={entry['active_devices']},working={entry['working_devices']})"
            for entry in parsed
            if entry['active_devices'] != entry['raid_devices'] or entry['working_devices'] != entry['raid_devices']
        ]
        missing_spare_disks = [
            f"Disk {entry['disk_number']}(spare={entry['spare_devices']})"
            for entry in parsed
            if require_spare_device and entry['spare_devices'] < 1
        ]

        if degraded_disks:
            return self.fail(
                'RAID 상태 이상 감지',
                message='일부 Storage Spaces RAID 상태가 정상(OK)이 아닙니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        if unhealthy_disks:
            return self.fail(
                'RAID 헬스 상태 이상 감지',
                message='일부 Storage Spaces RAID 헬스 상태가 Healthy가 아닙니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        if failed_device_disks:
            return self.fail(
                'RAID 실패 디스크 감지',
                message='실패한 디스크가 확인되었습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        if inactive_device_disks:
            return self.fail(
                'RAID 활성 디스크 수 불일치',
                message='활성 또는 정상 동작 디스크 수가 RAID 구성 디스크 수와 다릅니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        if missing_spare_disks:
            return self.fail(
                'RAID 스페어 디스크 미구성',
                message='스페어 디스크가 없어 자동 복구 구성이 부족합니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        primary = parsed[0]
        return self.ok(
            metrics={
                'raid_disk_count': len(parsed),
                'non_raid_disk_count': len(non_raid_lines),
                'primary_disk_number': primary['disk_number'],
                'primary_disk_name': primary['friendly_name'],
                'primary_state': primary['state'],
                'primary_health': primary['health'],
                'primary_raid_devices': primary['raid_devices'],
                'primary_active_devices': primary['active_devices'],
                'primary_working_devices': primary['working_devices'],
                'primary_failed_devices': primary['failed_devices'],
                'primary_spare_devices': primary['spare_devices'],
                'degraded_disks': degraded_disks,
                'unhealthy_disks': unhealthy_disks,
                'failed_device_disks': failed_device_disks,
                'inactive_device_disks': inactive_device_disks,
                'missing_spare_disks': missing_spare_disks,
                'matched_failure_keywords': matched_failure_keywords,
            },
            thresholds={
                'require_spare_device': require_spare_device,
                'failure_keywords': failure_keywords,
            },
            reasons='Storage Spaces RAID 상태, 헬스 상태, 활성 디스크 수가 모두 기준 범위 내입니다.',
            message='Windows 디스크 HA 점검이 정상 수행되었습니다.',
        )


CHECK_CLASS = Check
