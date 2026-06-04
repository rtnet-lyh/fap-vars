# -*- coding: utf-8 -*-

from .common._base import BaseCheck


COMMAND_ERROR_MARKERS = ('syntax error', 'unknown command', 'invalid command', 'unknown keyword', 'missing argument')
COMMAND = 'show services load-balancerpool'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'generic_network'
    PARAMIKO_REUSE_SESSION = True
    
    def run(self):
        # stdout, error = self._run_command(COMMAND)
        # if error:
        #     return error
        # metrics = {'output_line_count': len([line for line in stdout.splitlines() if line.strip()])}
        return self.ok(message='Junos EX4300에서 load-balancerpool 명령 점검이 지원되지 않습니다.')


CHECK_CLASS = Check
