# -*- coding: utf-8 -*-

from items.common._base import BaseCheck


CHECK_COMMAND = 'vmstat'
# ---------------------------------------------------------------------
# threshold 변수 가이드
# max_cpu_percent: 70
# max_io_wait_percent: 10
# ---------------------------------------------------------------------

class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def parse_output(self, output):
        lines = [line.strip() for line in (output or '').splitlines() if line.strip()]

        for index, line in enumerate(lines):
            headers = line.split()
            if not all(name in headers for name in ('us', 'sy', 'id', 'wa')):
                continue

            if index + 1 >= len(lines):
                return {'failure_type': 'parse_failure', 'reason': 'vmstat 데이터 행을 찾을 수 없습니다.'}

            values = lines[index + 1].split()
            if len(headers) != len(values):
                return {'failure_type': 'parse_failure', 'reason': 'vmstat 헤더와 데이터 열 개수가 일치하지 않습니다.'}

            try:
                idle_percent = float(values[headers.index('id')])
                io_wait_percent = float(values[headers.index('wa')])
            except Exception:
                return {'failure_type': 'parse_failure', 'reason': 'vmstat id/wa 값이 숫자가 아닙니다.'}

            return {
                'cpu_usage_percent': round(100.0 - idle_percent, 1),
                'io_wait_percent': round(io_wait_percent, 1),
                'idle_percent': round(idle_percent, 1),
            }

        return {'failure_type': 'parse_failure', 'reason': 'vmstat CPU 헤더를 찾을 수 없습니다.'}

    def evaluate(self, metrics, max_cpu_percent, max_io_wait_percent):
        if metrics.get('failure_type'):
            return 'fail'
        if metrics['cpu_usage_percent'] > max_cpu_percent:
            return 'fail'
        if metrics['io_wait_percent'] > max_io_wait_percent:
            return 'fail'
        return 'ok'

    def build_result(self, metrics, max_cpu_percent, max_io_wait_percent, status):
        criteria = f"""CPU 사용률 <= {max_cpu_percent:.1f}% 및 I/O wait <= {max_io_wait_percent:.1f}%,
            명령 실패, 파싱 실패 또는 기준 초과"""

        if metrics.get('failure_type') == 'command_failure':
            return {
                'message': 'vmstat 명령 실행에 실패했습니다.',
                'results': metrics.get('reason', '명령 실행에 실패했습니다.'),
                'criteria': criteria,
            }

        if metrics.get('failure_type') == 'parse_failure':
            return {
                'message': 'vmstat 출력 파싱에 실패했습니다.',
                'results': metrics.get('reason', '파싱에 실패했습니다.'),
                'criteria': criteria,
            }

        results = 'CPU 사용률 %.1f%%, I/O wait %.1f%%, idle %.1f%%' % (
            metrics['cpu_usage_percent'],
            metrics['io_wait_percent'],
            metrics['idle_percent'],
        )

        if status == 'ok':
            message = 'CPU 사용률 점검 양호'
        else:
            message = 'CPU 사용률이 기준을 초과했습니다.'

        return {
            'message': message,
            'results': results,
            'criteria': criteria,
        }

    def run(self):
        max_cpu_percent = self.get_threshold_var('max_cpu_percent', default=70.0, value_type='float')
        max_io_wait_percent = self.get_threshold_var('max_io_wait_percent', default=10.0, value_type='float')

        rc, output, error = self._ssh(CHECK_COMMAND)

        if rc != 0:
            metrics = {
                'failure_type': 'command_failure',
                'rc': rc,
                'reason': (error or output or 'vmstat 명령 실행에 실패했습니다.').strip(),
            }
        else:
            metrics = self.parse_output(output)

        status = self.evaluate(metrics, max_cpu_percent, max_io_wait_percent)
        result = self.build_result(metrics, max_cpu_percent, max_io_wait_percent, status)

        return self.result(
            status=status,
            message=result['message'],
            metrics=metrics,
            results=result['results'],
            criteria=result['criteria'],
        )


CHECK_CLASS = Check