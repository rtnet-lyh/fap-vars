# -*- coding: utf-8 -*-

import json

from .common._base import BaseCheck


POWERSHELL_SCRIPT_COMMAND = """
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$service = Get-Service -Name WinRM
$result = [PSCustomObject]@{
    ComputerName = $env:COMPUTERNAME
    WinRMStatus  = [string]$service.Status
    Is64Bit      = [Environment]::Is64BitOperatingSystem
}
$result | ConvertTo-Json -Depth 4
""".strip()


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'winrm'
    WINRM_SHELL = 'powershell'

    def run(self):
        rc, out, err = self._run_ps(POWERSHELL_SCRIPT_COMMAND)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'WinRM 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if self._is_not_applicable(rc, err):
            return self.fail(
                'WinRM 실행 환경을 사용할 수 없습니다.',
                message='PowerShell 스크립트 튜토리얼을 수행할 수 없습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='PowerShell 스크립트 예제 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        text = (out or '').strip()
        if not text:
            return self.fail(
                '출력 파싱 실패',
                message='PowerShell 스크립트 결과가 비어 있습니다.',
                stdout='',
                stderr=(err or '').strip(),
            )

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return self.fail(
                '출력 파싱 실패',
                message='PowerShell 스크립트 결과 JSON을 해석하지 못했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        computer_name = str(parsed.get('ComputerName', '')).strip()
        winrm_status = str(parsed.get('WinRMStatus', '')).strip()
        is_64bit = str(parsed.get('Is64Bit', '')).strip()

        if not computer_name or not winrm_status:
            return self.fail(
                '출력 파싱 실패',
                message='ComputerName 또는 WinRMStatus 필드를 찾지 못했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        return self.ok(
            metrics={
                'computer_name': computer_name,
                'winrm_status': winrm_status,
                'is_64bit': is_64bit,
            },
            thresholds={},
            reasons='multi-line PowerShell 스크립트 실행과 JSON 파싱을 정상 확인했습니다.',
            message=(
                '_run_ps PowerShell 스크립트 예제가 정상 수행되었습니다. '
                f'computer_name={computer_name}, winrm_status={winrm_status}'
            ),
        )


CHECK_CLASS = Check
