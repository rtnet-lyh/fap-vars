# -*- coding: utf-8 -*-

from .common._base import BaseCheck


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'

    PARAMIKO_AUTH_METHOD = 'password'
    PARAMIKO_PROFILE = {
        'pager_patterns': [r'--More--', r'Press any key'],
        'pager_response': ' ',
    }
    PARAMIKO_TIMEOUT_SEC = 10

    def run(self):
        results = self._run_paramiko_commands([
            'terminal length 0',
            'show kversion',
        ])

        failed = [item for item in results if item.get('rc') != 0]
        if failed:
            first = failed[0]
            if self._is_connection_error(first.get('rc'), first.get('stderr')):
                return self.fail(
                    '호스트 연결 실패',
                    message=(first.get('stderr') or 'Paramiko 연결 확인에 실패했습니다.').strip(),
                    stderr=(first.get('stderr') or '').strip(),
                )
            return self.fail(
                '점검 명령 실행 실패',
                message=f"{first.get('command')} 명령 실행에 실패했습니다.",
                stdout=(first.get('stdout') or '').strip(),
                stderr=(first.get('stderr') or '').strip(),
            )

        disable_paging_output = (results[0].get('stdout') or '').strip()
        show_version_output = (results[1].get('stdout') or '').strip()

        metrics = {
            'disable_paging_output': disable_paging_output,
            'show_version': show_version_output,
            'commands': [item.get('command') for item in results],
        }
        if not show_version_output:
            return self.fail(
                'show version 출력 없음',
                message='show version 명령 출력이 비어 있습니다.',
                stdout=show_version_output,
            )

        return self.ok(
            metrics=metrics,
            thresholds={},
            reasons='Paramiko 방식으로 show version 명령을 정상 수집했습니다.',
            message='Paramiko 테스트 점검이 정상 수행되었습니다.',
        )


CHECK_CLASS = Check
