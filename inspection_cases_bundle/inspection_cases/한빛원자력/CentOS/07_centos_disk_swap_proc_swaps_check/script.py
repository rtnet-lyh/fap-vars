# -*- coding: utf-8 -*-

import re

from items.common._base import BaseCheck


CHECK_COMMAND = 'cat /proc/swaps'
# ---------------------------------------------------------------------
# threshold 변수 가이드
# max_disk_swap_percent = 50
# ---------------------------------------------------------------------

class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'


    def parse_output(self, output):
        entries = []
        for line in (output or '').splitlines():
            parts = line.split()
            if len(parts) < 5 or parts[0].lower() == 'filename':
                continue
            try:
                size = float(parts[2])
                used = float(parts[3])
            except Exception:
                return {'failure_type': 'parse_failure', 'reason': 'swap 크기/사용량 값이 숫자가 아닙니다.'}
            usage = 0.0 if size <= 0 else round(used / size * 100.0, 1)
            entries.append({'device': parts[0], 'usage_percent': usage})
        if not entries:
            return {'failure_type': 'parse_failure', 'reason': '/proc/swaps에서 swap 장치 행을 찾을 수 없습니다.'}
        return {'swap_devices': entries, 'max_disk_swap_percent': max(item['usage_percent'] for item in entries)}

    def evaluate(self, metrics, max_disk_swap_percent):
        if metrics.get('failure_type'):
            return 'fail'
        return 'fail' if metrics['max_disk_swap_percent'] > max_disk_swap_percent else 'ok'

    def build_result(self, metrics, max_disk_swap_percent, status):
        criteria = '모든 swap 장치 사용률 <= %.1f%%' % max_disk_swap_percent
        if metrics.get('failure_type'):
            return {'message': 'swap 장치 사용률 점검 실패', 'results': metrics.get('reason', ''), 'criteria': criteria}
        results = 'swap 장치 수=%d, 최대 swap 사용률=%.1f%%' % (len(metrics['swap_devices']), metrics['max_disk_swap_percent'])
        message = 'swap 장치 사용률 점검 양호' if status == 'ok' else 'swap 장치 사용률이 기준을 초과했습니다.'
        return {'message': message, 'results': results, 'criteria': criteria}

    def run(self):
        max_disk_swap_percent = self.get_threshold_var('max_disk_swap_percent', default=50.0, value_type='float')

        rc, output, error = self._ssh(CHECK_COMMAND)

        if rc != 0:
            metrics = {
                'failure_type': 'command_failure',
                'rc': rc,
                'reason': (error or output or '명령 실행에 실패했습니다.').strip(),
            }
        else:
            metrics = self.parse_output(output)

        status = self.evaluate(metrics, max_disk_swap_percent)
        result = self.build_result(metrics, max_disk_swap_percent, status)

        return self.result(
            status=status,
            message=result['message'],
            metrics=metrics,
            results=result['results'],
            criteria=result['criteria'],
        )


CHECK_CLASS = Check