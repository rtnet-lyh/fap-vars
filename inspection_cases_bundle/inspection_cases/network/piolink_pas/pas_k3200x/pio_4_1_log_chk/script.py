# -*- coding: utf-8 -*-

import re
from datetime import datetime

from .common._base import BaseCheck


COMMAND = 'show log keyword {today}'
BAD_LOG_RE = re.compile(r'\((?:err|fail|down|stop|warning)\)', re.IGNORECASE)


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'generic_network'
    PARAMIKO_REUSE_SESSION = True

    def _run_command(self):
        today = datetime.now().strftime("%Y/%m/%d")
        results = self._run_paramiko_commands([COMMAND.format(today=today)], profile=self.PARAMIKO_PROFILE)
        if not results:
            return None, self.fail('점검 명령 실행 실패', message='Paramiko 명령 실행 결과가 비어 있습니다.')
        result = results[0]
        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()
        if result.get('rc') not in [0, 124]:
            return None, self.fail('점검 명령 실행 실패', message=f'{COMMAND} 명령 실행에 실패했습니다.', stdout=stdout, stderr=stderr)
        return stdout, None

    def run(self):
        stdout, error = self._run_command()
        if error:
            return error

        log_lines = [line.strip() for line in (stdout or '').splitlines() if line.strip()]
        bad_logs = [line for line in log_lines if BAD_LOG_RE.search(line)]
        metrics = {
            'log_line_count': len(log_lines),
            'bad_log_count': len(bad_logs),
            'bad_logs': bad_logs,
        }
        if bad_logs:
            return self.fail(error="치명 또는 경고 로그 패턴이 확인되었습니다.", metrics=metrics, thresholds={}, reasons='치명 또는 경고 로그 패턴이 확인되었습니다.', message=f'시스템 로그 경고: 대상 로그 {len(bad_logs)}건.')
        return self.ok(metrics=metrics, thresholds={}, reasons='(err), (fail), (down), (stop), (warning) 로그가 확인되지 않았습니다.', message=f'시스템 로그 점검 정상: 로그 {len(log_lines)}건 확인.')


CHECK_CLASS = Check
