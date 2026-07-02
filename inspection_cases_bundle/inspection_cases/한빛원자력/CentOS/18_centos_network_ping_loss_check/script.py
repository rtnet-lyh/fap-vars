# -*- coding: utf-8 -*-

import re

from items.common._base import BaseCheck


CHECK_COMMAND = "ping -c 5 $(ip route | awk '/default/ {print $3; exit}')"
# ---------------------------------------------------------------------
# threshold 변수 가이드
# max_packet_loss_percent: 0
# max_avg_response_ms: 100
# ---------------------------------------------------------------------

class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_AUTH_TIMEOUT_SEC = 30

    def parse_output(self, output):
        text = output or ''
        loss_match = re.search(r'(\d+(?:\.\d+)?)%\s*packet loss', text)
        rtt_match = re.search(r'=\s*([0-9.]+)/([0-9.]+)/([0-9.]+)/', text)
        if not loss_match:
            return {'failure_type': 'parse_failure', 'reason': 'ping 출력에서 패킷 손실 행을 찾을 수 없습니다.'}
        metrics = {'packet_loss_percent': float(loss_match.group(1))}
        if rtt_match:
            metrics['avg_response_ms'] = float(rtt_match.group(2))
        else:
            metrics['avg_response_ms'] = None
        return metrics

    def evaluate(self, metrics, max_packet_loss_percent, max_avg_response_ms):
        if metrics.get('failure_type'):
            return 'fail'
        if metrics['packet_loss_percent'] > max_packet_loss_percent:
            return 'fail'
        if metrics['avg_response_ms'] is not None and metrics['avg_response_ms'] > max_avg_response_ms:
            return 'fail'
        return 'ok'

    def build_result(self, metrics, max_packet_loss_percent, max_avg_response_ms, status):
        criteria = '패킷 손실률 <= %.1f%% 및 평균 응답시간 <= %.1f ms' % (max_packet_loss_percent, max_avg_response_ms)
        if metrics.get('failure_type'):
            return {'message': 'ping 점검 실패', 'results': metrics.get('reason', ''), 'criteria': criteria}
        results = '패킷 손실률=%.1f%%, 평균 응답시간=%s ms' % (metrics['packet_loss_percent'], metrics['avg_response_ms'])
        message = 'ping 손실률 점검 양호' if status == 'ok' else 'ping 손실률 또는 응답시간이 기준을 초과했습니다.'
        return {'message': message, 'results': results, 'criteria': criteria}

    def run(self):
        max_packet_loss_percent = self.get_threshold_var('max_packet_loss_percent', default=0.0, value_type='float')
        max_avg_response_ms = self.get_threshold_var('max_avg_response_ms', default=100.0, value_type='float')

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

        status = self.evaluate(metrics, max_packet_loss_percent, max_avg_response_ms)
        result = self.build_result(metrics, max_packet_loss_percent, max_avg_response_ms, status)

        return self.result(
            status=status,
            message=result['message'],
            metrics=metrics,
            results=result['results'],
            criteria=result['criteria'],
        )


CHECK_CLASS = Check