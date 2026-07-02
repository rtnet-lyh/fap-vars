# -*- coding: utf-8 -*-

from items.common._base import BaseCheck


CHECK_COMMAND = 'sysctl -a'
# ---------------------------------------------------------------------
# threshold 변수 가이드
#
# ---------------------------------------------------------------------

class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_AUTH_TIMEOUT_SEC = 30

    def parse_output(self, output):
        lines = [line.strip() for line in (output or '').splitlines() if line.strip()]
        data_lines = lines[1:]
        parameter_lines = [line for line in data_lines if '=' in line]
        return {
            'line_count': len(lines),
            'data_line_count': len(data_lines),
            'parameter_count': len(parameter_lines),
            'has_kernel_info': bool(data_lines),
        }

    def evaluate(self, metrics):
        if metrics.get('failure_type'):
            return 'fail'
        if metrics['has_kernel_info']:
            return 'ok'
        return 'fail'

    def build_result(self, metrics, status):
        criteria = 'sysctl -a 실행 결과에서 커널 파라미터 출력이 확인되어야 함'
        if metrics.get('failure_type') == 'command_failure':
            return {
                'message': 'sysctl -a 명령 실행에 실패했습니다.',
                'results': metrics.get('reason', ''),
                'criteria': criteria,
            }

        results = '출력 라인 수=%d, 커널 정보 라인 수=%d, 파라미터 라인 수=%d' % (
            metrics['line_count'],
            metrics['data_line_count'],
            metrics['parameter_count'],
        )
        message = '커널 파라미터 정보를 성공적으로 확인했습니다.' if status == 'ok' else '헤더 다음 커널 파라미터 정보가 없습니다.'
        return {'message': message, 'results': results, 'criteria': criteria}

    def run(self):
        results = self._run_paramiko_commands(CHECK_COMMAND, become=True)
        last = results[-1] if results else {}

        rc = last.get('rc', 1)
        output = last.get('stdout', '')
        error = last.get('stderr', '')

        if rc != 0:
            metrics = {
                'failure_type': 'command_failure',
                'rc': rc,
                'reason': (error or output or '명령 실행에 실패했습니다.').strip(),
            }
        else:
            metrics = self.parse_output(output)

        status = self.evaluate(metrics)
        result = self.build_result(metrics, status)

        return self.result(
            status=status,
            message=result['message'],
            metrics=metrics,
            results=result['results'],
            criteria=result['criteria'],
        )


CHECK_CLASS = Check