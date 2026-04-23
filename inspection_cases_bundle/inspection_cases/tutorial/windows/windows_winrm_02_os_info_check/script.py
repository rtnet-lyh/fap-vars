# -*- coding: utf-8 -*-

import json

from .common._base import BaseCheck


OS_INFO_COMMAND = (
    "$OutputEncoding = [System.Text.UTF8Encoding]::new($false); "
    "[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); "
    "Get-CimInstance Win32_OperatingSystem | "
    "Select-Object Caption, Version, CSName, LastBootUpTime | "
    "ConvertTo-Json -Depth 4"
)


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'winrm'
    WINRM_SHELL = 'powershell'

    def run(self):
        rc, out, err = self._run_ps(OS_INFO_COMMAND)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'WinRM 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if self._is_not_applicable(rc, err):
            return self.fail(
                'WinRM 실행 환경을 사용할 수 없습니다.',
                message='Windows OS 정보 튜토리얼을 수행할 수 없습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='OS 정보 조회 PowerShell 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        text = (out or '').strip()
        if not text:
            return self.fail(
                '출력 파싱 실패',
                message='OS 정보 결과가 비어 있습니다.',
                stdout='',
                stderr=(err or '').strip(),
            )

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return self.fail(
                '출력 파싱 실패',
                message='OS 정보 JSON을 해석하지 못했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        caption = str(parsed.get('Caption', '')).strip()
        version = str(parsed.get('Version', '')).strip()
        computer_name = str(parsed.get('CSName', '')).strip()
        last_boot_up_time = str(parsed.get('LastBootUpTime', '')).strip()

        if not caption or not computer_name:
            return self.fail(
                '출력 파싱 실패',
                message='Caption 또는 CSName 필드를 찾지 못했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        return self.ok(
            metrics={
                'caption': caption,
                'version': version,
                'computer_name': computer_name,
                'last_boot_up_time': last_boot_up_time,
            },
            thresholds={},
            reasons='Win32_OperatingSystem 핵심 필드를 정상 파싱했습니다.',
            message=f'OS 정보 예제가 정상 수행되었습니다. caption={caption}, version={version}',
        )


CHECK_CLASS = Check
