# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


COMMAND = 'show vlan'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'generic_network'
    PARAMIKO_REUSE_SESSION = True

    def _run_command(self):
        results = self._run_paramiko_commands([COMMAND], profile=self.PARAMIKO_PROFILE)
        if not results:
            return None, self.fail('점검 명령 실행 실패', message='Paramiko 명령 실행 결과가 비어 있습니다.')
        result = results[0]
        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()
        if result.get('rc') != 0:
            return None, self.fail('점검 명령 실행 실패', message=f'{COMMAND} 명령 실행에 실패했습니다.', stdout=stdout, stderr=stderr)
        return stdout, None

    def _parse_vlans(self, text):
        vlans = []
        for line in (text or '').splitlines():
            if '|' not in line:
                continue
            parts = [part.strip() for part in line.split('|')]
            if len(parts) < 3:
                continue
            name = parts[0]
            vlan_id = parts[1]
            if not vlan_id.isdigit():
                continue
            member_text = ' '.join(parts[2:])
            member_count = len(re.findall(r'(?<!\S)[ut](?!\S)', member_text, re.IGNORECASE))
            vlans.append({
                'name': name,
                'vlan_id': int(vlan_id),
                'member_count': member_count,
            })
        return vlans

    def run(self):
        min_vlan_member_count = self.get_threshold_var('min_vlan_member_count', default=1, value_type='int')
        thresholds = {'min_vlan_member_count': min_vlan_member_count}
        stdout, error = self._run_command()
        if error:
            return error

        vlans = self._parse_vlans(stdout)
        if not vlans:
            return self.fail('VLAN 파싱 실패', message='show vlan 출력에서 VLAN ID 행을 찾지 못했습니다.', stdout=stdout, thresholds=thresholds)

        evaluated_vlans = [item for item in vlans if item['vlan_id'] != 1 or item['member_count'] > 0]
        below_threshold = [item for item in evaluated_vlans if item['member_count'] < min_vlan_member_count]
        metrics = {
            'vlan_count': len(vlans),
            'evaluated_vlan_count': len(evaluated_vlans),
            'vlans_below_member_threshold': below_threshold,
            'vlans': vlans,
        }
        if not evaluated_vlans:
            return self.warn(metrics=metrics, thresholds=thresholds, reasons='멤버 포트가 있는 VLAN을 찾지 못했습니다.', message='VLAN 상태 경고: 멤버 포트가 있는 VLAN이 없습니다.')
        if below_threshold:
            return self.warn(metrics=metrics, thresholds=thresholds, reasons='일부 VLAN의 member port 수가 기준 미만입니다.', message=f'VLAN 상태 경고: 기준 미달 VLAN {len(below_threshold)}개.')
        return self.ok(metrics=metrics, thresholds=thresholds, reasons='VLAN별 member port 수가 기준 이상입니다.', message=f'VLAN 상태 점검 정상: 평가 VLAN {len(evaluated_vlans)}개.')


CHECK_CLASS = Check
