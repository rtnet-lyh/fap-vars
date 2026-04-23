# -*- coding: utf-8 -*-

from .common._base import BaseCheck


CLOCK_COMMAND = 'show clock'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'cisco_ios'

    def _run_with_enable(self, command_items):
        enable_password = str(self.get_connection_value('en_password', '') or '')
        if not enable_password:
            return None, self.fail(
                'enable 비밀번호 없음',
                message='connection credential에 en_password가 필요합니다.',
            )

        results = self._run_paramiko_commands([
            {
                'command': 'enable',
                'ignore_prompt': True,
            },
            {
                'command': enable_password,
                'hide_command': True,
            },
        ] + list(command_items))

        failed = [
            item for item in results
            if item.get('rc') != 0 and not (item.get('command') == 'enable' and item.get('timed_out'))
        ]
        if failed:
            first = failed[0]
            display_command = first.get('display_command') or first.get('command')
            return None, self.fail(
                '점검 명령 실행 실패',
                message=f'{display_command} 명령 실행에 실패했습니다.',
                stdout=(first.get('stdout') or '').strip(),
                stderr=(first.get('stderr') or '').strip(),
            )

        if len(results) < 2:
            return None, self.fail(
                'enable 모드 진입 실패',
                message='enable 명령 처리 결과가 부족합니다.',
            )

        enable_prompt = str(results[1].get('prompt') or '').strip()
        if not enable_prompt.endswith('#'):
            return None, self.fail(
                'enable 모드 진입 실패',
                message='enable 비밀번호 입력 후 privileged prompt(#)를 확인하지 못했습니다.',
                stdout=(results[1].get('stdout') or '').strip(),
                stderr=(results[1].get('stderr') or '').strip(),
            )

        return results, None

    def run(self):
        results, error = self._run_with_enable([
            {
                'command': CLOCK_COMMAND,
            },
        ])
        if error:
            return error

        clock_output = (results[2].get('stdout') or '').strip()
        if not clock_output:
            return self.fail(
                '시계 출력 없음',
                message='show clock 결과가 비어 있습니다.',
                stdout='',
            )

        return self.ok(
            metrics={
                'clock_output': clock_output,
                'commands': [item.get('display_command') or item.get('command') for item in results],
            },
            thresholds={},
            reasons='show clock 결과를 정상 수집했습니다.',
            message=f'_run_paramiko_commands 기본 예제가 정상 수행되었습니다. clock="{clock_output}"',
        )


CHECK_CLASS = Check
