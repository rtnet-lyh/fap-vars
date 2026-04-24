# -*- coding: utf-8 -*-
# UI single-file starter template
# 1. 이 파일은 SSH / WinRM / Paramiko 예시를 한 곳에 모아둔 학습용 starter다.
# 2. 실제 구현할 때는 아래 3개 클래스 중 내 환경에 맞는 클래스 하나만 남기면 된다.
# 3. 각 클래스는 동작 예시보다 "어떻게 작성하는지"를 보여주는 데 목적이 있다.

import json

from .common._base import BaseCheck


SSH_COMMAND = 'hostname && whoami'

POWERSHELL_SCRIPT = """
$result = [PSCustomObject]@{
    ComputerName = $env:COMPUTERNAME
    SampleStatus = "OK"
}
$result | ConvertTo-Json -Depth 4
""".strip()

PARAMIKO_COMMANDS = [
    # 긴 출력이 필요하면 아래 예시를 주석 해제한다.
    # {'command': 'terminal length 0'},
    {'command': 'show clock'},
]


class Check(BaseCheck):
    # SSH 예시: Rocky/Linux 계열에서 가장 자주 보는 기본 형태
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def run(self):
        # threshold가 필요하면 아래 패턴을 참고해서 추가한다.
        # max_usage_percent = self.get_threshold_var(
        #     'max_usage_percent',
        #     default=80,
        #     value_type='int',
        # )

        rc, out, err = self._ssh(SSH_COMMAND)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'SSH 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='SSH 예시 명령 실행에 실패했습니다. SSH_COMMAND를 점검 목적에 맞게 수정하세요.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        lines = [line.strip() for line in (out or '').splitlines() if line.strip()]
        if len(lines) < 2:
            return self.fail(
                '출력 파싱 실패',
                message='예시 출력에서 hostname과 로그인 사용자를 찾지 못했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        hostname = lines[0]
        login_user = lines[-1]

        return self.ok(
            metrics={
                'example_type': 'ssh',
                'hostname': hostname,
                'login_user': login_user,
            },
            thresholds={},
            reasons='SSH starter 예시입니다.',
            message=f'SSH starter 예시입니다. hostname={hostname}, login_user={login_user}',
        )


class Check(BaseCheck):
    # WinRM 예시: Windows 계열에서 PowerShell + JSON 파싱을 보여주는 기본 형태
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'winrm'
    WINRM_SHELL = 'powershell'

    def run(self):
        # threshold가 필요하면 아래 패턴을 참고해서 추가한다.
        # min_disk_count = self.get_threshold_var(
        #     'min_disk_count',
        #     default=1,
        #     value_type='int',
        # )

        rc, out, err = self._run_ps(POWERSHELL_SCRIPT)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'WinRM 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if self._is_not_applicable(rc, err):
            return self.fail(
                'WinRM 실행 환경을 사용할 수 없습니다.',
                message='WinRM 또는 PowerShell 실행 환경을 사용할 수 없습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='PowerShell 예시 스크립트 실행에 실패했습니다. POWERSHELL_SCRIPT를 수정하세요.',
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

        return self.ok(
            metrics={
                'example_type': 'winrm',
                'computer_name': computer_name,
                'sample_status': sample_status,
            },
            thresholds={},
            reasons='WinRM starter 예시입니다.',
            message=(
                'WinRM starter 예시입니다. '
                f'computer_name={computer_name}, sample_status={sample_status or "EMPTY"}'
            ),
        )


class Check(BaseCheck):
    # Paramiko 예시: Cisco IOS 계열에서 interactive shell 명령 배열을 보여주는 기본 형태
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'cisco_ios'

    def run(self):
        # threshold가 필요하면 아래 패턴을 참고해서 추가한다.
        # min_up_interface_count = self.get_threshold_var(
        #     'min_up_interface_count',
        #     default=1,
        #     value_type='int',
        # )

        # enable 모드가 필요하면 아래 패턴을 참고한다.
        # enable_password = str(self.get_connection_value('en_password', '') or '')
        # command_items = [
        #     {'command': 'enable', 'ignore_prompt': True},
        #     {'command': enable_password, 'hide_command': True},
        # ] + list(PARAMIKO_COMMANDS)

        results = self._run_paramiko_commands(PARAMIKO_COMMANDS)
        failed = [item for item in results if item.get('rc') != 0]
        if failed:
            first = failed[0]
            display_command = first.get('display_command') or first.get('command')
            return self.fail(
                '점검 명령 실행 실패',
                message=f'{display_command} 명령 실행에 실패했습니다.',
                stdout=(first.get('stdout') or '').strip(),
                stderr=(first.get('stderr') or '').strip(),
            )

        if not results:
            return self.fail(
                '명령 실행 결과 없음',
                message='Paramiko 실행 결과가 비어 있습니다.',
            )

        last_result = results[-1]
        command_output = (last_result.get('stdout') or '').strip()
        if not command_output:
            return self.fail(
                '출력 파싱 실패',
                message='마지막 명령의 stdout이 비어 있습니다.',
                stdout='',
                stderr=(last_result.get('stderr') or '').strip(),
            )

        return self.ok(
            metrics={
                'example_type': 'paramiko',
                'command_count': len(results),
                'last_command': last_result.get('display_command') or last_result.get('command'),
                'command_output': command_output,
            },
            thresholds={},
            reasons='Paramiko starter 예시입니다.',
            message=(
                'Paramiko starter 예시입니다. '
                f'last_command={last_result.get("display_command") or last_result.get("command")}'
            ),
        )


# 학습용 파일이라 3개 클래스를 함께 둔다.
CHECK_CLASS = Check
