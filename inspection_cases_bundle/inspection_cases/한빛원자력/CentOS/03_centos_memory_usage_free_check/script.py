# -*- coding: utf-8 -*-

import re

from items.common._base import BaseCheck


CHECK_COMMAND = 'free -m'
# ---------------------------------------------------------------------
# threshold 변수 가이드
# max_memory_percent: 80
# min_available_percent: 20
# ---------------------------------------------------------------------

class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'


    def parse_output(self, output):
        for line in (output or '').splitlines():
            parts = line.split()
            if not parts or parts[0].rstrip(':').lower() != 'mem':
                continue
            if len(parts) < 7:
                return {'failure_type': 'parse_failure', 'reason': 'free -m Mem 행의 열 개수가 부족합니다.'}
            try:
                total = float(parts[1])
                used = float(parts[2])
                available = float(parts[6])
            except Exception:
                return {'failure_type': 'parse_failure', 'reason': 'free -m 메모리 값이 숫자가 아닙니다.'}
            if total <= 0:
                return {'failure_type': 'parse_failure', 'reason': 'free -m 총 메모리 값이 0입니다.'}
            return {'memory_usage_percent': round(used / total * 100.0, 1), 'available_percent': round(available / total * 100.0, 1)}
        return {'failure_type': 'parse_failure', 'reason': 'free -m Mem 행을 찾을 수 없습니다.'}

    def evaluate(self, metrics, max_memory_percent, min_available_percent):
        if metrics.get('failure_type'):
            return 'fail'
        if metrics['memory_usage_percent'] > max_memory_percent:
            return 'fail'
        if metrics['available_percent'] < min_available_percent:
            return 'fail'
        return 'ok'

    def build_result(self, metrics, max_memory_percent, min_available_percent, status):
        criteria = '메모리 사용률 <= %.1f%% 및 가용 메모리 비율 >= %.1f%%' % (max_memory_percent, min_available_percent)
        if metrics.get('failure_type'):
            return {'message': '메모리 사용률 점검 실패', 'results': metrics.get('reason', ''), 'criteria': criteria}
        results = '메모리 사용률=%.1f%%, 가용 메모리 비율=%.1f%%' % (metrics['memory_usage_percent'], metrics['available_percent'])
        message = '메모리 사용률 점검 양호' if status == 'ok' else '메모리 사용률이 기준을 초과했습니다.'
        return {'message': message, 'results': results, 'criteria': criteria}

    def run(self):
        max_memory_percent = self.get_threshold_var('max_memory_percent', default=80.0, value_type='float')
        min_available_percent = self.get_threshold_var('min_available_percent', default=20.0, value_type='float')

        rc, output, error = self._ssh(CHECK_COMMAND)

        if rc != 0:
            metrics = {
                'failure_type': 'command_failure',
                'rc': rc,
                'reason': (error or output or '명령 실행에 실패했습니다.').strip(),
            }
        else:
            metrics = self.parse_output(output)

        status = self.evaluate(metrics, max_memory_percent, min_available_percent)
        result = self.build_result(metrics, max_memory_percent, min_available_percent, status)

        return self.result(
            status=status,
            message=result['message'],
            metrics=metrics,
            results=result['results'],
            criteria=result['criteria'],
        )


CHECK_CLASS = Check