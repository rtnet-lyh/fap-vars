# -*- coding: utf-8 -*-

from .common._base import BaseCheck


CHECK_COMMAND = 'show version'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def run(self):
        enable_password = str(self.get_connection_value('en_password', '') or '')

        with self._open_terminal() as term:
            try:
                term.use_profile('cisco_ios')
                privilege_escalation_used = term.enter_privilege(password=enable_password)
                term.disable_paging()
                result = term.run_command(CHECK_COMMAND, timeout_sec=30)
            except Exception as exc:
                return self.fail(
                    'Interactive terminal 예외',
                    message=str(exc),
                    stdout=term.buffer,
                )

        if not result.output:
            return self.fail(
                '명령 결과 없음',
                message=f'{CHECK_COMMAND} 명령 출력이 비어 있습니다.',
                stdout=result.raw_output,
            )

        return self.ok(
            metrics={
                'connection': 'ssh_terminal',
                'platform': 'cisco_ios',
                'check_command': CHECK_COMMAND,
                'command_output': result.output,
                'prompt': result.prompt,
                'privilege_escalation_used': privilege_escalation_used,
            },
            thresholds={},
            reasons='Cisco IOS terminal profile로 권한 상승 후 명령 결과를 수집했습니다.',
            message='Cisco IOS terminal command 점검이 정상 수행되었습니다.',
        )


CHECK_CLASS = Check
