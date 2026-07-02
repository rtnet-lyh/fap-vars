# -*- coding: utf-8 -*-

import re

from items.common._base import BaseCheck


CHECK_COMMAND = 'ip link'
# ---------------------------------------------------------------------
# threshold 변수 가이드
# target_interface: 운영 기준 NIC
# nic_link_state: UP
# nic_required_flags: UP|LOWER_UP
# ---------------------------------------------------------------------

class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_AUTH_TIMEOUT_SEC = 30

    def parse_output(self, output):
        interfaces = []
        for line in (output or '').splitlines():
            match = re.match(r'^\d+:\s+([^:]+):\s+<([^>]*)>.*\sstate\s+(\S+)', line.strip())
            if match:
                interfaces.append({
                    'name': match.group(1).split('@')[0],
                    'flags': [item.strip() for item in match.group(2).split(',')],
                    'state': match.group(3),
                })
        if not interfaces:
            return {'failure_type': 'parse_failure', 'reason': 'ip link 출력에서 인터페이스 행을 찾을 수 없습니다.'}
        return {'interfaces': interfaces, 'interface_count': len(interfaces)}

    def evaluate(self, metrics, target_interface, nic_link_state, nic_required_flags):
        if metrics.get('failure_type'):
            return 'fail'
        targets = [item.strip() for item in re.split(r'[|,\n]+', target_interface or '') if item.strip()]
        required_flags = [item.strip() for item in re.split(r'[|,\n]+', nic_required_flags or '') if item.strip()]
        selected = [item for item in metrics['interfaces'] if item['name'] != 'lo' and (not targets or item['name'] in targets)]
        if not selected:
            metrics['policy_violations'] = ['점검 대상 인터페이스를 찾을 수 없습니다.']
            return 'fail'
        bad = []
        for iface in selected:
            if iface['state'].upper() != nic_link_state.upper():
                bad.append('%s 상태가 기준값과 다릅니다.' % iface['name'])
            missing_flags = [flag for flag in required_flags if flag not in iface['flags']]
            if missing_flags:
                bad.append('%s 필수 플래그 누락: %s' % (iface['name'], ', '.join(missing_flags)))
        metrics['checked_interfaces'] = selected
        metrics['policy_violations'] = bad
        return 'fail' if bad else 'ok'

    def build_result(self, metrics, target_interface, nic_link_state, nic_required_flags, status):
        criteria = '선택된 NIC 상태가 %s이고 플래그에 %s 포함' % (nic_link_state, nic_required_flags)
        if metrics.get('failure_type'):
            return {'message': '네트워크 링크 점검 실패', 'results': metrics.get('reason', ''), 'criteria': criteria}
        results = '인터페이스 수=%d, 점검 대상 수=%d' % (metrics['interface_count'], len(metrics.get('checked_interfaces', [])))
        message = '네트워크 링크 점검 양호' if status == 'ok' else '네트워크 링크 상태가 기준을 만족하지 않습니다.'
        return {'message': message, 'results': results, 'criteria': criteria}

    def run(self):
        target_interface = self.get_threshold_var('target_interface', default='', value_type='str')
        nic_link_state = self.get_threshold_var('nic_link_state', default='UP', value_type='str')
        nic_required_flags = self.get_threshold_var('nic_required_flags', default='UP|LOWER_UP', value_type='str')

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

        status = self.evaluate(metrics, target_interface, nic_link_state, nic_required_flags)
        result = self.build_result(metrics, target_interface, nic_link_state, nic_required_flags, status)

        return self.result(
            status=status,
            message=result['message'],
            metrics=metrics,
            results=result['results'],
            criteria=result['criteria'],
        )


CHECK_CLASS = Check