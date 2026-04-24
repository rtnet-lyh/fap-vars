# -*- coding: utf-8 -*-
# Windows UI starter template
# 1. POWERSHELL_SCRIPT 내용을 점검 목적에 맞게 먼저 수정한다.
# 2. run() 안에서는 self._run_ps(...)로 PowerShell을 실행한다.
# 3. 마지막에는 self.ok(...) 또는 self.fail(...) 중 하나를 반환한다.

import json

from .common._base import BaseCheck


# Step 1. 가장 먼저 이 PowerShell 스크립트를 바꾼다.
POWERSHELL_SCRIPT = """
$result = [PSCustomObject]@{
    ComputerName = $env:COMPUTERNAME
    SampleStatus = "OK"
}
$result | ConvertTo-Json -Depth 4
""".strip()


class Check(BaseCheck):
    # Step 2. Windows 기본 연결 방식은 winrm + powershell 이다.
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'winrm'
    WINRM_SHELL = 'powershell'

    def run(self):
        # Step 3. threshold가 필요하면 아래 패턴을 주석 해제해서 사용한다.
        # min_disk_count = self.get_threshold_var(
        #     'min_disk_count',
        #     default=1,
        #     value_type='int',
        # )

        # Step 4. PowerShell 실행
        rc, out, err = self._run_ps(POWERSHELL_SCRIPT)

        # Step 5-a. WinRM 연결 자체가 실패했는지 먼저 확인한다.
        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'WinRM 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        # Step 5-b. WinRM 사용 자체가 어려운 환경인지 구분한다.
        if self._is_not_applicable(rc, err):
            return self.fail(
                'WinRM 실행 환경을 사용할 수 없습니다.',
                message='WinRM 또는 PowerShell 실행 환경을 사용할 수 없습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        # Step 5-c. 명령 실행 실패를 별도로 구분한다.
        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='PowerShell 예시 스크립트 실행에 실패했습니다. POWERSHELL_SCRIPT를 환경에 맞게 수정하세요.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        text = (out or '').strip()
        if not text:
            return self.fail(
                '출력 파싱 실패',
                message='PowerShell 실행 결과가 비어 있습니다.',
                stdout='',
                stderr=(err or '').strip(),
            )

        # Step 5-d. PowerShell 결과는 가능한 한 JSON으로 고정하면 파싱이 쉽다.
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return self.fail(
                '출력 파싱 실패',
                message='PowerShell 결과 JSON을 해석하지 못했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        computer_name = str(parsed.get('ComputerName', '')).strip()
        sample_status = str(parsed.get('SampleStatus', '')).strip()
        if not computer_name:
            return self.fail(
                '출력 파싱 실패',
                message='ComputerName 필드를 찾지 못했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        # Step 6. 필요한 값만 metrics에 남기고 사람이 읽을 메시지를 작성한다.
        return self.ok(
            metrics={
                'computer_name': computer_name,
                'sample_status': sample_status,
            },
            thresholds={},
            reasons='Windows starter template이 PowerShell 실행과 JSON 파싱 흐름을 보여줍니다.',
            message=(
                'Windows starter 예시입니다. '
                f'computer_name={computer_name}, sample_status={sample_status or "EMPTY"}'
            ),
        )


CHECK_CLASS = Check
