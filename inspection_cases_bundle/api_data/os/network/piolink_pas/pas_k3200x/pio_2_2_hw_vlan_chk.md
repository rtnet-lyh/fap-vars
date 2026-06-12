# type_name

일상점검

# area_name

상태점검

# category_name

network

# application_type

piolink_pas

# application

pas_k3200x

# inspection_code

NETWORK-PIOLINK-PAS-K3200X-HW-VLAN-01

# is_required

권고

# inspection_name

VLAN 상태 점검

# inspection_content

VLAN 상태 및 Tagging 확인

# inspection_command

```bash
show vlan
```

# inspection_output

```text

```

# description

- VLAN ID: 어떤 VLAN인지 표시
- u: VLAN untagged member port
- t: VLAN tagged member port
- .: VLAN 미소속 포트
※ VLAN ID 다음 컬럼은 포트 번호(순서대로 1~24번 포트까지 표시되어 있음)
※ 예를 들어 Port 4, 16, 17, 18, 19 가 VLAN 422에 untagged member로 소속되어 있음

- **양호**: VLAN ID가 존재하며, member port(u/t)가 `min_vlan_member_count`개 이상 존재하는 경우
- **경고**: VLAN ID가 존재하지 않거나, member port(u/t)가 `min_vlan_member_count`가 미만인 경우
- **확인 필요**: 명령어 수행 실패 또는 출력 결과를 확인할 수 없는 경우

# thresholds

[
    {id: null, key: "min_vlan_member_count", value: "1", sortOrder: 0}
]

# inspection_script

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
            return self.fail(error="멤버 포트가 있는 VLAN을 찾지 못했습니다.", metrics=metrics, thresholds=thresholds, reasons='멤버 포트가 있는 VLAN을 찾지 못했습니다.', message='VLAN 상태 경고: 멤버 포트가 있는 VLAN이 없습니다.')
        if below_threshold:
            return self.fail(error="일부 VLAN의 member port 수가 기준 미만입니다.", metrics=metrics, thresholds=thresholds, reasons='일부 VLAN의 member port 수가 기준 미만입니다.', message=f'VLAN 상태 경고: 기준 미달 VLAN {len(below_threshold)}개.')
        return self.ok(metrics=metrics, thresholds=thresholds, reasons='VLAN별 member port 수가 기준 이상입니다.', message=f'VLAN 상태 점검 정상: 평가 VLAN {len(evaluated_vlans)}개.')


CHECK_CLASS = Check
