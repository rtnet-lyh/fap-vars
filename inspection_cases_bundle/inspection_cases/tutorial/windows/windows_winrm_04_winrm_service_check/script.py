# -*- coding: utf-8 -*-

import json

from .common._base import BaseCheck


WINRM_SERVICE_COMMAND = (
    "$OutputEncoding = [System.Text.UTF8Encoding]::new($false); "
    "[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); "
    "Get-Service -Name WinRM | "
    "Select-Object Name, Status, StartType, DisplayName | "
    "ConvertTo-Json -Depth 4"
)

SERVICE_STATUS_MAP = {
    '1': 'Stopped',
    '2': 'StartPending',
    '3': 'StopPending',
    '4': 'Running',
    '5': 'ContinuePending',
    '6': 'PausePending',
    '7': 'Paused',
}

SERVICE_START_TYPE_MAP = {
    '0': 'Boot',
    '1': 'System',
    '2': 'Automatic',
    '3': 'Manual',
    '4': 'Disabled',
}


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'winrm'
    WINRM_SHELL = 'powershell'

    def run(self):
        expected_status = self.get_threshold_var('expected_status', default='Running', value_type='str')
        rc, out, err = self._run_ps(WINRM_SERVICE_COMMAND)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'WinRM 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if self._is_not_applicable(rc, err):
            return self.fail(
                'WinRM 실행 환경을 사용할 수 없습니다.',
                message='WinRM 서비스 상태 튜토리얼을 수행할 수 없습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='WinRM 서비스 조회 PowerShell 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        text = (out or '').strip()
        if not text:
            return self.fail(
                '출력 파싱 실패',
                message='WinRM 서비스 결과가 비어 있습니다.',
                stdout='',
                stderr=(err or '').strip(),
            )

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return self.fail(
                '출력 파싱 실패',
                message='WinRM 서비스 JSON을 해석하지 못했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        service_name = str(parsed.get('Name', '')).strip()
        status_raw = str(parsed.get('Status', '')).strip()
        start_type_raw = str(parsed.get('StartType', '')).strip()
        status = SERVICE_STATUS_MAP.get(status_raw, status_raw)
        start_type = SERVICE_START_TYPE_MAP.get(start_type_raw, start_type_raw)
        display_name = str(parsed.get('DisplayName', '')).strip()

        if not service_name or not status:
            return self.fail(
                '출력 파싱 실패',
                message='Name 또는 Status 필드를 찾지 못했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        if status.lower() != expected_status.lower():
            return self.fail(
                '서비스 상태 비정상',
                message=(
                    f'WinRM 서비스 상태가 기대값과 다릅니다: '
                    f'actual={status}, expected={expected_status}'
                ),
                stdout=text,
                stderr=(err or '').strip(),
            )

        return self.ok(
            metrics={
                'service_name': service_name,
                'display_name': display_name,
                'status': status,
                'start_type': start_type,
            },
            thresholds={
                'expected_status': expected_status,
            },
            reasons='WinRM 서비스 상태가 기대값과 일치합니다.',
            message=f'서비스 상태 예제가 정상 수행되었습니다. {service_name}={status}',
        )


CHECK_CLASS = Check
