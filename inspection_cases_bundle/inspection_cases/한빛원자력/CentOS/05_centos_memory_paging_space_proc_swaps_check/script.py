# -*- coding: utf-8 -*-

import re

from items.common._base import BaseCheck


CHECK_COMMAND = 'cat /proc/swaps'
# ---------------------------------------------------------------------
# threshold 변수 가이드
# max_paging_space_percent: 50
# expected_swap_configured: true
# ---------------------------------------------------------------------

class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'


    def parse_output(self, output):
        total = 0.0
        used = 0.0
        for line in (output or '').splitlines():
            parts = line.split()
            if len(parts) < 5 or parts[0].lower() == 'filename':
                continue
            try:
                total += float(parts[2])
                used += float(parts[3])
            except Exception:
                return {'failure_type': 'parse_failure', 'reason': 'swap 크기/사용량 값이 숫자가 아닙니다.'}
        if total <= 0:
            return {'swap_configured': False, 'paging_space_percent': 0.0}
        return {'swap_configured': True, 'paging_space_percent': round(used / total * 100.0, 1)}

    def evaluate(self, metrics, max_paging_space_percent, expected_swap_configured):
        if metrics.get('failure_type'):
            return 'fail'
        if bool(metrics['swap_configured']) != bool(expected_swap_configured):
            return 'fail'
        if metrics['paging_space_percent'] > max_paging_space_percent:
            return 'fail'
        return 'ok'

    def build_result(self, metrics, max_paging_space_percent, expected_swap_configured, status):
        criteria = 'swap 구성 기대값=%s이고 페이징 사용률 <= %.1f%%' % (expected_swap_configured, max_paging_space_percent)
        if metrics.get('failure_type'):
            return {'message': '페이징 공간 점검 실패', 'results': metrics.get('reason', ''), 'criteria': criteria}
        results = 'swap 구성 여부=%s, 페이징 공간 사용률=%.1f%%' % (metrics['swap_configured'], metrics['paging_space_percent'])
        message = '페이징 공간 점검 양호' if status == 'ok' else '페이징 공간 사용률이 기준을 초과했습니다.'
        return {'message': message, 'results': results, 'criteria': criteria}

    def run(self):
        max_paging_space_percent = self.get_threshold_var('max_paging_space_percent', default=50.0, value_type='float')
        expected_swap_configured = self.get_threshold_var('expected_swap_configured', default=True, value_type='bool')

        rc, output, error = self._ssh(CHECK_COMMAND)

        if rc != 0:
            metrics = {
                'failure_type': 'command_failure',
                'rc': rc,
                'reason': (error or output or '명령 실행에 실패했습니다.').strip(),
            }
        else:
            metrics = self.parse_output(output)

        status = self.evaluate(metrics, max_paging_space_percent, expected_swap_configured)
        result = self.build_result(metrics, max_paging_space_percent, expected_swap_configured, status)

        return self.result(
            status=status,
            message=result['message'],
            metrics=metrics,
            results=result['results'],
            criteria=result['criteria'],
        )


CHECK_CLASS = Check