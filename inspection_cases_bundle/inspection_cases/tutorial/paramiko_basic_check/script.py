# -*- coding: utf-8 -*-

from .common._base import BaseCheck


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'huawei_vrp'

    def run(self):
        commands = [
            {
                'command': 'screen-length 0 temp',                
            },
            {
                'command': 'test',                
                'hide_command': True,
            },
            {
                'command': 'display version',
            },
        ]
        results = self._run_paramiko_commands(commands)

        connection_failed = [
            item for item in results
            if self._is_connection_error(item.get('rc'), item.get('stderr'))
        ]
        if connection_failed:
            first = connection_failed[0]
            return self.fail(
                '호스트 연결 실패',
                message=(first.get('stderr') or 'Paramiko 연결 확인에 실패했습니다.').strip(),
                stderr=(first.get('stderr') or '').strip(),
            )

        result_by_command = {item.get('command'): item for item in results}
        timeout_commands = [item.get('command') for item in results if item.get('timed_out')]

        whoami_result = result_by_command.get('screen-length 0 temp', {})
        hostname_result = result_by_command.get('test', {})
        os_release_result = result_by_command.get('display version', {})

        user_output = (whoami_result.get('stdout') or '').strip()
        hostname_output = (hostname_result.get('stdout') or '').strip()
        os_release_output = (os_release_result.get('stdout') or '').strip()

        metrics = {
            'login_user': user_output,
            'hostname': hostname_output,
            'os_release_line_count': len([line for line in os_release_output.splitlines() if line.strip()]),
            'commands': [item.get('command') for item in results],
            'timeout_commands': timeout_commands,
        }
        if not user_output:
            return self.fail(
                'whoami 출력 없음',
                message='whoami 명령 출력이 비어 있습니다.',
                stdout=(whoami_result.get('stdout') or '').strip(),
                stderr=(whoami_result.get('stderr') or '').strip(),
            )
        if not hostname_output:
            return self.fail(
                'hostname 출력 없음',
                message='hostname 명령 출력이 비어 있습니다.',
                stdout=(hostname_result.get('stdout') or '').strip(),
                stderr=(hostname_result.get('stderr') or '').strip(),
            )
        if not os_release_output:
            return self.fail(
                'OS 정보 출력 없음',
                message='/etc/os-release 출력이 비어 있습니다.',
                stdout=(os_release_result.get('stdout') or '').strip(),
                stderr=(os_release_result.get('stderr') or '').strip(),
            )

        reasons = 'Paramiko 방식으로 Linux 기본 명령을 수집했습니다.'
        message = f'Paramiko Linux 테스트 점검이 정상 수행되었습니다. user={user_output}, hostname={hostname_output}'
        if timeout_commands:
            reasons += ' 일부 입력은 prompt timeout 후 계속 진행했습니다.'
            message += f", timeout_commands={', '.join(timeout_commands)}"

        return self.ok(
            metrics=metrics,
            thresholds={},
            reasons=reasons,
            message=message,
        )


CHECK_CLASS = Check
