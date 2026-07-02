# -*- coding: utf-8 -*-

import re

from items.common._base import BaseCheck


CHECK_COMMAND = 'for h in /sys/class/fc_host/host*; do [ -d "$h" ] && echo "[$(basename "$h")] $(cat "$h"/port_state 2>/dev/null) $(cat "$h"/speed 2>/dev/null)"; done; true'
# ---------------------------------------------------------------------
# threshold 변수 가이드
# hba_port_state: Online
# expected_hba_ports: 운영 기준 포트 수
# ---------------------------------------------------------------------

class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'


    def parse_output(self, output):
        ports = []
        for line in (output or '').splitlines():
            match = re.match(r'\[(?P<host>[^\]]+)\]\s+(?P<state>\S+)(?:\s+(?P<speed>.*))?$', line.strip())
            if match:
                ports.append({'host': match.group('host'), 'state': match.group('state'), 'speed': (match.group('speed') or '').strip()})
        if not ports:
            return {'not_applicable': True, 'reason': 'fc_host 포트를 찾을 수 없어 점검 대상에서 제외합니다.'}
        return {'hba_port_count': len(ports), 'ports': ports}

    def evaluate(self, metrics, hba_port_state, expected_hba_ports):
        if metrics.get('not_applicable'):
            return 'excluded'
        if metrics.get('failure_type'):
            return 'fail'
        if expected_hba_ports and metrics['hba_port_count'] < expected_hba_ports:
            return 'fail'
        bad = [port for port in metrics['ports'] if port['state'].lower() != hba_port_state.lower()]
        metrics['bad_ports'] = bad
        return 'fail' if bad else 'ok'

    def build_result(self, metrics, hba_port_state, expected_hba_ports, status):
        criteria = 'HBA 포트 상태가 %s이고 포트 수 >= %d' % (hba_port_state, expected_hba_ports)
        if metrics.get('not_applicable'):
            return {'message': 'HBA 연결 점검 대상이 아닙니다.', 'results': metrics.get('reason', ''), 'criteria': criteria}
        results = 'HBA 포트 수=%d' % metrics.get('hba_port_count', 0)
        message = 'HBA 연결 점검 양호' if status == 'ok' else 'HBA 연결 상태가 기준을 만족하지 않습니다.'
        return {'message': message, 'results': results, 'criteria': criteria}

    def run(self):
        hba_port_state = self.get_threshold_var('hba_port_state', default='Online', value_type='str')
        expected_hba_ports = self.get_threshold_var('expected_hba_ports', default=0, value_type='int')

        rc, output, error = self._ssh(CHECK_COMMAND)

        if rc != 0:
            metrics = {
                'failure_type': 'command_failure',
                'rc': rc,
                'reason': (error or output or '명령 실행에 실패했습니다.').strip(),
            }
        else:
            metrics = self.parse_output(output)

        status = self.evaluate(metrics, hba_port_state, expected_hba_ports)
        result = self.build_result(metrics, hba_port_state, expected_hba_ports, status)

        return self.result(
            status=status,
            message=result['message'],
            metrics=metrics,
            results=result['results'],
            criteria=result['criteria'],
        )


CHECK_CLASS = Check