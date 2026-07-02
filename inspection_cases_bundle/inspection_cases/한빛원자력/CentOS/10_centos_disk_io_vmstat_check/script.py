# -*- coding: utf-8 -*-

import re

from items.common._base import BaseCheck


CHECK_COMMAND = 'vmstat'
# ---------------------------------------------------------------------
# threshold 변수 가이드
# max_blocked_processes = 1
# max_io_wait_percent = 1.0
# ---------------------------------------------------------------------

class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'


    def parse_output(self, output):
        lines = [line.strip() for line in (output or '').splitlines() if line.strip()]
        for index, line in enumerate(lines):
            headers = line.split()
            if not all(name in headers for name in ('b', 'wa')):
                continue
            if index + 1 >= len(lines):
                return {'failure_type': 'parse_failure', 'reason': 'vmstat 데이터 행을 찾을 수 없습니다.'}
            values = lines[index + 1].split()
            if len(values) != len(headers):
                return {'failure_type': 'parse_failure', 'reason': 'vmstat 헤더와 데이터 열 개수가 일치하지 않습니다.'}
            try:
                return {'blocked_processes': int(values[headers.index('b')]), 'io_wait_percent': float(values[headers.index('wa')])}
            except Exception:
                return {'failure_type': 'parse_failure', 'reason': 'vmstat b/wa 값이 숫자가 아닙니다.'}
        return {'failure_type': 'parse_failure', 'reason': 'vmstat b/wa 헤더를 찾을 수 없습니다.'}

    def evaluate(self, metrics, max_blocked_processes, max_io_wait_percent):
        if metrics.get('failure_type'):
            return 'fail'
        if metrics['blocked_processes'] > max_blocked_processes:
            return 'fail'
        if metrics['io_wait_percent'] > max_io_wait_percent:
            return 'fail'
        return 'ok'

    def build_result(self, metrics, max_blocked_processes, max_io_wait_percent, status):
        criteria = '블록된 프로세스 수 <= %d 및 I/O wait <= %.1f%%' % (max_blocked_processes, max_io_wait_percent)
        if metrics.get('failure_type'):
            return {'message': 'vmstat 디스크 I/O 점검 실패', 'results': metrics.get('reason', ''), 'criteria': criteria}
        results = '블록된 프로세스 수=%d, I/O wait=%.1f%%' % (metrics['blocked_processes'], metrics['io_wait_percent'])
        message = '디스크 I/O 점검 양호' if status == 'ok' else '디스크 I/O 상태가 기준을 만족하지 않습니다.'
        return {'message': message, 'results': results, 'criteria': criteria}

    def run(self):
        max_blocked_processes = self.get_threshold_var('max_blocked_processes', default=1, value_type='int')
        max_io_wait_percent = self.get_threshold_var('max_io_wait_percent', default=1.0, value_type='float')

        rc, output, error = self._ssh(CHECK_COMMAND)

        if rc != 0:
            metrics = {
                'failure_type': 'command_failure',
                'rc': rc,
                'reason': (error or output or '명령 실행에 실패했습니다.').strip(),
            }
        else:
            metrics = self.parse_output(output)

        status = self.evaluate(metrics, max_blocked_processes, max_io_wait_percent)
        result = self.build_result(metrics, max_blocked_processes, max_io_wait_percent, status)

        return self.result(
            status=status,
            message=result['message'],
            metrics=metrics,
            results=result['results'],
            criteria=result['criteria'],
        )


CHECK_CLASS = Check