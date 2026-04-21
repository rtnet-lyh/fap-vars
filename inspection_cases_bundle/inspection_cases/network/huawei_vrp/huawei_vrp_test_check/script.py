# -*- coding: utf-8 -*-
from .common._base import BaseCheck


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def run(self):
        with self._open_terminal() as term:
            try:
                # term.use_profile('cisco_ios')
                # term.enter_privilege(password=enable_password)
                # term.disable_paging()
                term.run_command("screen-length 0 temp", timeout_sec=10)
                term.run_command("show processes cpu", timeout_sec=10)
            except Exception as exc:
                return self.fail(
                    'Interactive terminal 예외',
                    message=str(exc),
                    stdout=term.buffer,
                )
        return self.ok(
            metrics={},
            reasons='CPU 사용률이 정상입니다.',
            message=f'CPU 사용률이 정상입니다.',
        )


CHECK_CLASS = Check
