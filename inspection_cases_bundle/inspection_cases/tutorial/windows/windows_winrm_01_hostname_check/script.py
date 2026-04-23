# -*- coding: utf-8 -*-

from .common._base import BaseCheck


HOSTNAME_COMMAND = 'hostname'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'winrm'
    WINRM_SHELL = 'powershell'

    def run(self):
        rc, out, err = self._run_ps(HOSTNAME_COMMAND)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'WinRM 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if self._is_not_applicable(rc, err):
            return self.fail(
                'WinRM 실행 환경을 사용할 수 없습니다.',
                message='Windows hostname 튜토리얼을 수행할 수 없습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='hostname 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        hostname = (out or '').strip()
        if not hostname:
            return self.fail(
                '출력 파싱 실패',
                message='hostname 결과가 비어 있습니다.',
                stdout='',
                stderr=(err or '').strip(),
            )

        return self.ok(
            metrics={
                'hostname': hostname,
            },
            thresholds={},
            reasons='hostname 문자열을 정상 수집했습니다.',
            message=f'_run_ps 기본 예제가 정상 수행되었습니다. hostname={hostname}',
        )


CHECK_CLASS = Check
