# type_name

일상점검

# area_name

상태점검

# category_name

network

# application_type

nx_os

# application

mds_c9148s

# inspection_code

NETWORK-NXOS-MDS-C9148S-ROUTE-01

# is_required

권고

# inspection_name

라우팅 Table 상태

# inspection_content

라우팅 Table 정상 여부 확인

# inspection_command

```bash
show ip route
```

# inspection_output

```text

```

# description

- 명령어: IP 라우팅 테이블 상태를 확인하는 명령어
- Default Route가 목적지 경로를 찾지 못할 때 트래픽을 전송할 경로인 기본 gateway로 설정되어있어야함.

[참고]
1안. gateway값을 변수로 받아 일치하면 양호처리.
2안. 출력만 하고 담당자 확인처리.

- **양호**: `gateway_ip`와 'Default gateway is `gateway_ip`' 일치 상태
- **경고**: `gateway_ip`와 'Default gateway is `gateway_ip`' 불 일치 상태
- **확인 필요**: 명령어 실패 및 파싱 불가

# thresholds

[
    {id: null, key: "gateway_ip", value: "193.1.0.254", sortOrder: 0}
]

# inspection_script

# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


COMMAND = 'show ip route'
GATEWAY_RE = re.compile(r'Default gateway is\s+(\d+(?:\.\d+){3})')


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'
    SSH_CONTROL_MASTER = False

    def run(self):
        expected = str(self.get_threshold_var('gateway_ip', default='193.1.0.254', value_type='str')).strip()
        thresholds = {'gateway_ip': expected}
        if not expected:
            return self.fail('임계치 미정의', message='gateway_ip 값이 필요합니다.', thresholds=thresholds)

        rc, out, err = self._ssh(COMMAND)
        if rc != 0:
            return self.fail('점검 명령 실행 실패', message=f'{COMMAND} 명령 실행에 실패했습니다.', stdout=(out or '').strip(), stderr=(err or '').strip(), thresholds=thresholds)

        match = GATEWAY_RE.search(out or '')
        if not match:
            return self.fail('라우팅 테이블 파싱 실패', message='Default gateway 값을 찾지 못했습니다.', stdout=(out or '').strip(), thresholds=thresholds)

        actual = match.group(1)
        metrics = {'default_gateway': actual}
        if actual != expected:
            return self.warn(metrics=metrics, thresholds=thresholds, reasons=f'Default gateway {actual}가 기준 {expected}와 다릅니다.', message='Default gateway 기준 불일치')
        return self.ok(metrics=metrics, thresholds=thresholds, reasons='Default gateway가 기준값과 일치합니다.', message='라우팅 테이블 점검이 정상 수행되었습니다.')


CHECK_CLASS = Check
