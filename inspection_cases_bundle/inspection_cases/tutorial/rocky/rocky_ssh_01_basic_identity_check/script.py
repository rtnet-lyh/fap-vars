# -*- coding: utf-8 -*-

from .common._base import BaseCheck


IDENTITY_COMMAND = 'hostname && whoami'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def run(self):
        rc, out, err = self._ssh(IDENTITY_COMMAND)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'SSH 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='hostname && whoami 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        lines = [line.strip() for line in (out or '').splitlines() if line.strip()]
        if len(lines) < 2:
            return self.fail(
                '출력 파싱 실패',
                message='hostname 또는 whoami 결과를 해석하지 못했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        hostname = lines[0]
        login_user = lines[-1]

        return self.ok(
            metrics={
                'hostname': hostname,
                'login_user': login_user,
            },
            thresholds={},
            reasons='hostname과 로그인 사용자를 정상 수집했습니다.',
            message=f'_ssh 기본 예제가 정상 수행되었습니다. hostname={hostname}, user={login_user}',
        )


CHECK_CLASS = Check
