# -*- coding: utf-8 -*-

from .common._base import BaseCheck


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'winrm'
    WINRM_SHELL = 'powershell'

    def run(self):
        cmd = "Write-Output 'USER=Administrator'; Write-Output 'HOST=WIN-DEMO'"
        rc, out, err = self._run_ps(cmd)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'WinRM 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if self._is_not_applicable(rc, err):
            return self.not_applicable(
                'WinRM 실행 환경을 사용할 수 없습니다.',
                raw_output=(err or '').strip(),
            )

        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='Windows replay 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        result_map = {}
        for line in (out or '').splitlines():
            if '=' not in line:
                continue
            key, value = line.split('=', 1)
            result_map[key.strip().lower()] = value.strip()

        return self.ok(
            metrics={
                'connection': 'winrm',
                'user': result_map.get('user', ''),
                'host': result_map.get('host', ''),
            },
            reasons='WinRM replay 응답을 확인했습니다.',
            message='Windows replay 점검이 정상 수행되었습니다.',
        )


CHECK_CLASS = Check
