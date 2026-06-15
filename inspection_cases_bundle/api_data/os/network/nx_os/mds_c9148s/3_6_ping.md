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


NW-NX-MDS9148-011

# is_required

권고

# inspection_name

통신 테스트

# inspection_content

특정 장비와 통신상태 정상 확인.

# inspection_command

```bash
ping `ping_ip` count 5
```

# inspection_output

```text

```

# description

- 명령어: 특정 대상 IP와 통신 가능여부를 5회 확인하는 명령어.
- received가 5면 정상 판단 가능
- 통신 확인 할 IP를 호스트 변수로 받아와야함.

- **양호**: 결과 값 내 '5 received' 문자 포함
- **경고**: 결과 값 내 '5 received' 문자 미 포함
- **확인 필요**: 명령어 실패 및 `ping_ip` 변수 미 선언, 파싱 불가

# thresholds

[
    {id: null, key: "ping_ip", value: "193.1.0.207", sortOrder: 0}
]

# inspection_script

# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


COUNT = 5
STATS_RE = re.compile(r'(\d+) packets transmitted,\s*(\d+) received.*?([0-9.]+)% packet loss')


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'
    SSH_CONTROL_MASTER = False

    def run(self):
        ping_ip = str(self.get_threshold_var('ping_ip', default='193.1.0.207', value_type='str')).strip()
        thresholds = {'ping_ip': ping_ip, 'ping_count': COUNT}
        if not ping_ip:
            return self.fail('임계치 미정의', message='ping_ip 값이 필요합니다.', thresholds=thresholds)

        command = f'ping {ping_ip} count {COUNT}'
        rc, out, err = self._ssh(command)
        if rc != 0:
            return self.fail('점검 명령 실행 실패', message=f'{command} 명령 실행에 실패했습니다.', stdout=(out or '').strip(), stderr=(err or '').strip(), thresholds=thresholds)

        match = STATS_RE.search(out or '')
        if not match:
            return self.fail('ping 결과 파싱 실패', message='ping statistics를 해석하지 못했습니다.', stdout=(out or '').strip(), thresholds=thresholds)

        sent, received, loss = int(match.group(1)), int(match.group(2)), float(match.group(3))
        metrics = {'packets_transmitted': sent, 'packets_received': received, 'packet_loss_percent': loss}
        if received != COUNT:
            return self.warn(metrics=metrics, thresholds=thresholds, reasons=f'{COUNT} received 조건을 만족하지 못했습니다.', message=f'ping 수신 패킷 부족: received={received}.')
        return self.ok(metrics=metrics, thresholds=thresholds, reasons=f'{COUNT} received 조건을 만족했습니다.', message='통신 테스트가 정상 수행되었습니다.')


CHECK_CLASS = Check
