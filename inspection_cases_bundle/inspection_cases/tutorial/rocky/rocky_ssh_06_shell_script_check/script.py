# -*- coding: utf-8 -*-

import shlex

from .common._base import BaseCheck


SCRIPT_COMMAND = "bash -lc " + shlex.quote(
    "\n".join([
        "hostname_value=$(hostname)",
        "uptime_value=$(uptime)",
        "printf 'HOSTNAME=%s\\n' \"$hostname_value\"",
        "printf 'UPTIME=%s\\n' \"$uptime_value\"",
    ])
)


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def run(self):
        rc, out, err = self._ssh(SCRIPT_COMMAND)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'SSH 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='bash -lc 스크립트 예제 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        hostname = ''
        uptime_text = ''
        for raw_line in (out or '').splitlines():
            line = raw_line.strip()
            if line.startswith('HOSTNAME='):
                hostname = line.split('=', 1)[1].strip()
            elif line.startswith('UPTIME='):
                uptime_text = line.split('=', 1)[1].strip()

        if not hostname or not uptime_text:
            return self.fail(
                '출력 파싱 실패',
                message='쉘 스크립트 출력에서 HOSTNAME 또는 UPTIME 라인을 찾지 못했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        return self.ok(
            metrics={
                'hostname': hostname,
                'uptime_text': uptime_text,
            },
            thresholds={},
            reasons='bash -lc 스크립트 실행과 출력 파싱을 정상 확인했습니다.',
            message=f'_ssh 쉘 스크립트 예제가 정상 수행되었습니다. hostname={hostname}',
        )


CHECK_CLASS = Check
