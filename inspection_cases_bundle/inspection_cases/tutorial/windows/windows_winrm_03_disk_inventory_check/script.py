# -*- coding: utf-8 -*-

import json

from .common._base import BaseCheck


DISK_INVENTORY_COMMAND = (
    "$OutputEncoding = [System.Text.UTF8Encoding]::new($false); "
    "[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); "
    "Get-CimInstance Win32_LogicalDisk -Filter \"DriveType=3\" | "
    "Select-Object DeviceID, VolumeName, Size, FreeSpace | "
    "ConvertTo-Json -Depth 4"
)


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
        min_fixed_disk_count = self.get_threshold_var('min_fixed_disk_count', default=1, value_type='int')
        rc, out, err = self._run_ps(DISK_INVENTORY_COMMAND)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'WinRM 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if self._is_not_applicable(rc, err):
            return self.fail(
                'WinRM 실행 환경을 사용할 수 없습니다.',
                message='Windows 디스크 인벤토리 튜토리얼을 수행할 수 없습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='디스크 인벤토리 PowerShell 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        text = (out or '').strip()
        if not text:
            return self.fail(
                '출력 파싱 실패',
                message='디스크 인벤토리 결과가 비어 있습니다.',
                stdout='',
                stderr=(err or '').strip(),
            )

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return self.fail(
                '출력 파싱 실패',
                message='디스크 인벤토리 JSON을 해석하지 못했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        disks = []
        for entry in _as_list(parsed):
            if not isinstance(entry, dict):
                continue
            device_id = str(entry.get('DeviceID', '')).strip()
            if not device_id:
                continue
            if entry.get('Size') is None or entry.get('FreeSpace') is None:
                continue
            try:
                size_bytes = int(str(entry.get('Size', '0')).strip())
                free_bytes = int(str(entry.get('FreeSpace', '0')).strip())
            except ValueError:
                return self.fail(
                    '출력 파싱 실패',
                    message='디스크 크기 값을 정수로 변환하지 못했습니다.',
                    stdout=text,
                    stderr=(err or '').strip(),
                )
            disks.append({
                'device_id': device_id,
                'volume_name': str(entry.get('VolumeName', '')).strip(),
                'size_bytes': size_bytes,
                'free_bytes': free_bytes,
            })

        if len(disks) < min_fixed_disk_count:
            return self.fail(
                '디스크 수 기준 미달',
                message=(
                    f'고정 디스크 수가 기준 미만입니다: '
                    f'{len(disks)}개 (기준 {min_fixed_disk_count}개 이상)'
                ),
                stdout=text,
                stderr=(err or '').strip(),
            )

        largest_disk = max(disks, key=lambda item: item['size_bytes'])

        return self.ok(
            metrics={
                'disk_count': len(disks),
                'largest_disk_device_id': largest_disk['device_id'],
                'largest_disk_size_bytes': largest_disk['size_bytes'],
                'disks': disks,
            },
            thresholds={
                'min_fixed_disk_count': min_fixed_disk_count,
            },
            reasons='고정 디스크 인벤토리를 정상 수집했습니다.',
            message=(
                '_run_ps 배열 JSON 예제가 정상 수행되었습니다. '
                f'disk_count={len(disks)}, largest_disk={largest_disk["device_id"]}'
            ),
        )


CHECK_CLASS = Check
