# -*- coding: utf-8 -*-

import re

from items.common._base import BaseCheck


CHECK_COMMAND = "printf 'CPU(s): '; grep -c '^processor' /proc/cpuinfo; printf 'On-line CPU(s) list: '; cat /sys/devices/system/cpu/online 2>/dev/null || echo 0"
# ---------------------------------------------------------------------
# threshold 변수 가이드
# expected_online_cpu: 전체 인식 CPU default 0
# offline_cpu_allowed: false
# ---------------------------------------------------------------------

class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'


    def parse_output(self, output):
        text = output or ''
        total_match = re.search(r'CPU\(s\):\s*(\d+)', text)
        online_match = re.search(r'On-line CPU\(s\) list:\s*([^\n]+)', text)
        if not total_match or not online_match:
            return {'failure_type': 'parse_failure', 'reason': 'CPU(s) 또는 On-line CPU(s) list 항목을 찾을 수 없습니다.'}
        total = int(total_match.group(1))
        online = []
        for token in online_match.group(1).replace(',', ' ').split():
            if '-' in token:
                start, end = [int(item) for item in token.split('-', 1)]
                online.extend(range(start, end + 1))
            else:
                online.append(int(token))
        online = sorted(set(online))
        return {'cpu_count': total, 'online_cpu_count': len(online), 'offline_cpu_count': max(total - len(online), 0), 'online_cpus': online}

    def evaluate(self, metrics, expected_online_cpu, offline_cpu_allowed):
        if metrics.get('failure_type'):
            return 'fail'
        expected = expected_online_cpu or metrics['cpu_count']
        if metrics['online_cpu_count'] < expected:
            return 'fail'
        if metrics['offline_cpu_count'] and not offline_cpu_allowed:
            return 'fail'
        return 'ok'

    def build_result(self, metrics, expected_online_cpu, offline_cpu_allowed, status):
        criteria = '온라인 CPU 수가 기대 수 이상이고 오프라인 CPU 허용 여부=%s' % offline_cpu_allowed
        if metrics.get('failure_type'):
            return {'message': 'CPU 코어 점검 실패', 'results': metrics.get('reason', ''), 'criteria': criteria}
        results = 'CPU 수=%d, 온라인 CPU 수=%d, 오프라인 CPU 수=%d' % (metrics['cpu_count'], metrics['online_cpu_count'], metrics['offline_cpu_count'])
        message = 'CPU 코어 점검 양호' if status == 'ok' else 'CPU 코어 상태가 기준을 만족하지 않습니다.'
        return {'message': message, 'results': results, 'criteria': criteria}

    def run(self):
        expected_online_cpu = self.get_threshold_var('expected_online_cpu', default=0, value_type='int')
        offline_cpu_allowed = self.get_threshold_var('offline_cpu_allowed', default=False, value_type='bool')

        rc, output, error = self._ssh(CHECK_COMMAND)

        if rc != 0:
            metrics = {
                'failure_type': 'command_failure',
                'rc': rc,
                'reason': (error or output or '명령 실행에 실패했습니다.').strip(),
            }
        else:
            metrics = self.parse_output(output)

        status = self.evaluate(metrics, expected_online_cpu, offline_cpu_allowed)
        result = self.build_result(metrics, expected_online_cpu, offline_cpu_allowed, status)

        return self.result(
            status=status,
            message=result['message'],
            metrics=metrics,
            results=result['results'],
            criteria=result['criteria'],
        )


CHECK_CLASS = Check