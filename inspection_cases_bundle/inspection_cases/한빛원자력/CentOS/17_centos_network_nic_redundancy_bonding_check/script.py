# -*- coding: utf-8 -*-

import re

from items.common._base import BaseCheck


CHECK_COMMAND = 'cat /proc/net/bonding/bond0 2>/dev/null || true'
# ---------------------------------------------------------------------
# threshold 변수 가이드
# bond_mii_status: up
# slave_mii_status: up
# max_link_failure_count: 0
# ---------------------------------------------------------------------

class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'


    def parse_output(self, output):
        text = output or ''
        if not text.strip():
            return {'not_applicable': True, 'reason': 'bond0 구성이 확인되지 않아 점검 대상에서 제외합니다.'}
        bond_status = ''
        active_slave = ''
        slaves = []
        current = None
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith('Currently Active Slave:'):
                active_slave = stripped.split(':', 1)[1].strip()
            elif stripped.startswith('MII Status:') and current is None:
                bond_status = stripped.split(':', 1)[1].strip()
            elif stripped.startswith('Slave Interface:'):
                current = {'interface': stripped.split(':', 1)[1].strip()}
                slaves.append(current)
            elif current is not None and ':' in stripped:
                key, value = stripped.split(':', 1)
                current[key.strip()] = value.strip()
        return {'bond_mii_status': bond_status, 'active_slave': active_slave, 'slave_count': len(slaves), 'slaves': slaves}

    def evaluate(self, metrics, bond_mii_status, slave_mii_status, max_link_failure_count):
        if metrics.get('not_applicable'):
            return 'excluded'
        if metrics.get('failure_type'):
            return 'fail'
        bad = []
        if metrics['bond_mii_status'].lower() != bond_mii_status.lower():
            bad.append('bond MII 상태가 기준값과 다릅니다.')
        if not metrics['active_slave']:
            bad.append('active slave가 확인되지 않습니다.')
        for slave in metrics['slaves']:
            if slave.get('MII Status', '').lower() != slave_mii_status.lower():
                bad.append('%s MII 상태가 기준값과 다릅니다.' % slave.get('interface', ''))
            try:
                if int(slave.get('Link Failure Count', '0')) > max_link_failure_count:
                    bad.append('%s 링크 실패 수가 기준을 초과했습니다.' % slave.get('interface', ''))
            except Exception:
                bad.append('%s 링크 실패 수를 파싱할 수 없습니다.' % slave.get('interface', ''))
        metrics['policy_violations'] = bad
        return 'fail' if bad else 'ok'

    def build_result(self, metrics, bond_mii_status, slave_mii_status, max_link_failure_count, status):
        criteria = f"""bond와 slave의 MII 상태가 up이고
활성 slave가 존재하며 링크 실패 수 <= {max_link_failure_count}"""
        if metrics.get('not_applicable'):
            return {'message': 'NIC 본딩 점검 대상이 아닙니다.', 'results': metrics.get('reason', ''), 'criteria': criteria}
        results = 'bond MII 상태=%s, 활성 slave=%s, slave 수=%d' % (metrics.get('bond_mii_status', ''), metrics.get('active_slave', ''), metrics.get('slave_count', 0))
        message = 'NIC 본딩 점검 양호' if status == 'ok' else 'NIC 본딩 상태가 기준을 만족하지 않습니다.'
        return {'message': message, 'results': results, 'criteria': criteria}

    def run(self):
        bond_mii_status = self.get_threshold_var('bond_mii_status', default='up', value_type='str')
        slave_mii_status = self.get_threshold_var('slave_mii_status', default='up', value_type='str')
        max_link_failure_count = self.get_threshold_var('max_link_failure_count', default=0, value_type='int')

        rc, output, error = self._ssh(CHECK_COMMAND)

        if rc != 0:
            metrics = {
                'failure_type': 'command_failure',
                'rc': rc,
                'reason': (error or output or '명령 실행에 실패했습니다.').strip(),
            }
        else:
            metrics = self.parse_output(output)

        status = self.evaluate(metrics, bond_mii_status, slave_mii_status, max_link_failure_count)
        result = self.build_result(metrics, bond_mii_status, slave_mii_status, max_link_failure_count, status)

        return self.result(
            status=status,
            message=result['message'],
            metrics=metrics,
            results=result['results'],
            criteria=result['criteria'],
        )


CHECK_CLASS = Check