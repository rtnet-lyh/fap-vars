# -*- coding: utf-8 -*-

import re

from items.common._base import BaseCheck


CHECK_COMMAND = 'df -h'
# ---------------------------------------------------------------------
# threshold 변수 가이드
# max_use_percent: 80
# critical_use_percent: 90
# min_avail_percent: 20
# ---------------------------------------------------------------------

class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'


    def parse_output(self, output):
        entries = []
        for line in (output or '').splitlines():
            parts = line.split()
            if len(parts) < 6 or not parts[4].endswith('%') or parts[0].lower() == 'filesystem':
                continue
            try:
                use_percent = int(parts[4].rstrip('%'))
            except Exception:
                return {'failure_type': 'parse_failure', 'reason': 'Use% 값이 숫자가 아닙니다.'}
            entries.append({'filesystem': parts[0], 'use_percent': use_percent, 'avail_percent': 100 - use_percent, 'mount_point': parts[5]})
        if not entries:
            return {'failure_type': 'parse_failure', 'reason': 'df -h 출력에서 파일시스템 행을 찾을 수 없습니다.'}
        return {'filesystems': entries, 'max_use_percent': max(item['use_percent'] for item in entries), 'min_avail_percent': min(item['avail_percent'] for item in entries)}

    def evaluate(self, metrics, max_use_percent, min_avail_percent):
        if metrics.get('failure_type'):
            return 'fail'
        if metrics['max_use_percent'] > max_use_percent:
            return 'fail'
        if metrics['min_avail_percent'] < min_avail_percent:
            return 'fail'
        return 'ok'

    def build_result(self, metrics, max_use_percent, critical_use_percent, min_avail_percent, status):
        criteria = 'Use%% <= %.1f%% 및 가용 공간 비율 >= %.1f%% / 위험 기준 참고 %.1f%%' % (max_use_percent, min_avail_percent, critical_use_percent)
        if metrics.get('failure_type'):
            return {'message': '파일시스템 사용률 점검 실패', 'results': metrics.get('reason', ''), 'criteria': criteria}
        results = '파일시스템 수=%d, 최대 사용률=%.1f%%, 최소 가용 비율=%.1f%%' % (len(metrics['filesystems']), metrics['max_use_percent'], metrics['min_avail_percent'])
        message = '파일시스템 사용률 점검 양호' if status == 'ok' else '파일시스템 사용률이 기준을 초과했습니다.'
        return {'message': message, 'results': results, 'criteria': criteria}

    def run(self):
        max_use_percent = self.get_threshold_var('max_use_percent', default=80.0, value_type='float')
        critical_use_percent = self.get_threshold_var('critical_use_percent', default=90.0, value_type='float')
        min_avail_percent = self.get_threshold_var('min_avail_percent', default=20.0, value_type='float')

        rc, output, error = self._ssh(CHECK_COMMAND)

        if rc != 0:
            metrics = {
                'failure_type': 'command_failure',
                'rc': rc,
                'reason': (error or output or '명령 실행에 실패했습니다.').strip(),
            }
        else:
            metrics = self.parse_output(output)

        status = self.evaluate(metrics, max_use_percent, min_avail_percent)
        result = self.build_result(metrics, max_use_percent, critical_use_percent, min_avail_percent, status)

        return self.result(
            status=status,
            message=result['message'],
            metrics=metrics,
            results=result['results'],
            criteria=result['criteria'],
        )


CHECK_CLASS = Check