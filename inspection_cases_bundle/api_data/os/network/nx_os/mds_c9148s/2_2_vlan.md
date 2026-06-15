# type_name

일상점검

# area_name

network

# category_name

상태점검

# application_type

nx_os

# application

mds_c9148s

# inspection_code


NW-NX-MDS9148-005

# is_required

권고

# inspection_name

VLAN 상태 점검

# inspection_content

VLAN 상태 확인

# inspection_command

```bash
show vsan
```

# inspection_output

```text
CITS-SAN1# show vsan
vsan 1 information
         name:VSAN0001  state:active
         interoperability mode:default
         loadbalancing:src-id/dst-id/oxid
         operational state:down

vsan 10 information
         name:VSAN0010  state:active
         interoperability mode:default
         loadbalancing:src-id/dst-id/oxid
         operational state:up

vsan 4079:evfp_isolated_vsan

vsan 4094:isolated_vsan
```

# description

- 명령어: 장비에 구성된 VSAN목록과 각 VSAN의 상태를 확인하는 명령어.
- 운영대상 VSAN의 state가 active 이면 정상 사용가능 상태.
- 운영대상 VSAN 리스트를 호스트 변수로 받아와야함.

[참고]
- VLAN 명령어를 사용해야하지만 해당 장비는 VLAN을 지원하지않는 장비로 VSAN으로 대체 점검함.
- 운영대상 VSAN 목록을 변수로 정의 하기 힘든 환경에서는 담당자확인필요 처리.

- **양호**: `active_vsan`에 포함된 VSAN의 state 값이 active인 경우
- **경고**: `active_vsan`에 포함된 VSAN의 state 값이 active가 아닌 경우
- **확인 필요**: 명령어 실패 및 `active_vsan` 변수 미 선언, 파싱 불가

# thresholds

[
    {id: null, key: "active_vsan", value: "10", sortOrder: 0}
]

# inspection_script

# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


COMMAND = 'show vsan'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'
    SSH_CONTROL_MASTER = False
    
    def _split(self, value):
        return [item for item in re.split(r'[\s,]+', str(value or '').strip()) if item]

    def _parse(self, text):
        vsans = {}
        current = None
        for line in (text or '').splitlines():
            info = re.search(r'^vsan\s+(\d+)\s+information', line.strip(), re.IGNORECASE)
            state = re.search(r'name:\S+\s+state:(\S+)', line.strip(), re.IGNORECASE)
            if info:
                current = info.group(1)
                vsans[current] = {}
            elif current and state:
                vsans[current]['state'] = state.group(1)
        return vsans

    def run(self):
        expected = self._split(self.get_threshold_var('active_vsan', default='10', value_type='str'))
        thresholds = {'active_vsan': expected}
        if not expected:
            return self.fail('임계치 미정의', message='active_vsan 값이 필요합니다.', thresholds=thresholds)

        rc, out, err = self._ssh(COMMAND)
        if rc != 0:
            return self.fail('점검 명령 실행 실패', message=f'{COMMAND} 명령 실행에 실패했습니다.', stdout=(out or '').strip(), stderr=(err or '').strip(), thresholds=thresholds)

        vsans = self._parse(out)
        if not vsans:
            return self.fail('VSAN 상태 파싱 실패', message='show vsan 결과를 해석하지 못했습니다.', stdout=(out or '').strip(), thresholds=thresholds)

        bad = [{'vsan': name, 'state': vsans.get(name, {}).get('state', 'missing')} for name in expected if vsans.get(name, {}).get('state') != 'active']
        metrics = {'checked_vsan_count': len(expected), 'bad_vsans': bad, 'vsans': vsans}
        if bad:
            return self.warn(metrics=metrics, thresholds=thresholds, reasons=f'{len(bad)}개 운영대상 VSAN이 active 상태가 아닙니다.', message='운영대상 VSAN 상태 기준 미달')
        return self.ok(metrics=metrics, thresholds=thresholds, reasons='운영대상 VSAN이 모두 active 상태입니다.', message='VSAN 상태 점검이 정상 수행되었습니다.')


CHECK_CLASS = Check
