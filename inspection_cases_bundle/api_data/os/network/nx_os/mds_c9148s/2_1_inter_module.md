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


NW-NX-MDS9148-004

# is_required

필수

# inspection_name

인터페이스/모듈 상태

# inspection_content

인터페이스 /모듈의 Down/Up 상태 점검

# inspection_command

```bash
show interface brief
```

# inspection_output

```text
CITS-SAN1# show interface brief

-------------------------------------------------------------------------------
Interface  Vsan   Admin  Admin   Status       SFP    Oper  Oper   Port
                  Mode   Trunk                       Mode  Speed  Channel
                         Mode                              (Gbps)
-------------------------------------------------------------------------------
fc1/1      10     auto   on      up           swl   F      8      --
fc1/2      10     auto   on      up           swl   F      8      --
fc1/3      10     auto   on      notConnected swl    --    --     --
fc1/4      10     auto   on      up           swl   F      8      --
fc1/5      10     auto   on      up           swl   F      8      --
fc1/6      10     auto   on      up           swl   F      8      --
fc1/7      10     auto   on      up           swl   F      8      --
fc1/8      10     auto   on      up           swl   F      8      --
fc1/9      10     auto   on      up           swl   F      8      --
fc1/10     10     auto   on      up           swl   F      8      --
fc1/11     10     auto   on      notConnected swl    --    --     --
fc1/12     10     auto   on      errDisabled  swl    --    --     --
fc1/13     1      auto   on      sfpAbsent    --     --    --     --
fc1/14     1      auto   on      licenseNotAv --     --    --     --
fc1/15     1      auto   on      sfpAbsent    --     --    --     --
```

# description

- 명령어: 인터페이스 상태를 요약하여 확인하는 명령어.
- 운영대상 인터페이스의 Status가 up 이면 정상 링크 업 상태.
- 운영대상 인터페이스를 호스트 변수로 받아와야함.

[참고]
- notconnected: 포트는 활성상태이나 물리링크가 연결되지 않았거나 상대 장비와 링크가 올라오지 않은 상태.
- sfpabsent: 모듈이 장착되지 않았거나, 인식을 못하는 상태.
- down: 인터페이스 다운 상태.
- 운영대상 인터페이스 목록을 변수로 정의 하기 힘든 환경에서는 담당자확인필요 처리.

- **양호**: `up_interface`에 포함된 인터페이스의 status 값이 up인 경우
- **경고**: `up_interface`에 포함된 인터페이스의 status 값이 up이 아닌 경우
- **확인 필요**: 명령어 실패 및 `up_interface` 변수 미 선언, 파싱 불가

# thresholds

[
    {id: null, key: "up_interface", value: "fc1/1,fc1/2,fc1/4,fc1/5,fc1/6,fc1/7,fc1/8,fc1/9,fc1/10", sortOrder: 0}
]

# inspection_script

# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck

COMMAND = 'show interface brief'
ROW_RE = re.compile(r'^(fc\S+)\s+\S+\s+\S+\s+\S+\s+(\S+)')

class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'
    SSH_CONTROL_MASTER = False

    def _split(self, value):
        return [item for item in re.split(r'[\s,]+', str(value or '').strip()) if item]

    def run(self):
        expected = self._split(self.get_threshold_var('up_interface', default='fc1/1,fc1/2', value_type='str'))
        thresholds = {'up_interface': expected}
        if not expected:
            return self.fail('임계치 미정의', message='up_interface 값이 필요합니다.', thresholds=thresholds)

        rc, out, err = self._ssh(COMMAND)
        if rc != 0:
            return self.fail('점검 명령 실행 실패', message=f'{COMMAND} 명령 실행에 실패했습니다.', stdout=(out or '').strip(), stderr=(err or '').strip(), thresholds=thresholds)

        statuses = {m.group(1): m.group(2) for m in (ROW_RE.match(line.strip()) for line in (out or '').splitlines()) if m}
        if not statuses:
            return self.fail('인터페이스 상태 파싱 실패', message='show interface brief 결과를 해석하지 못했습니다.', stdout=(out or '').strip(), thresholds=thresholds)

        bad = [{'interface': name, 'status': statuses.get(name, 'missing')} for name in expected if statuses.get(name) != 'up']
        metrics = {'checked_interface_count': len(expected), 'bad_interfaces': bad, 'interface_statuses': statuses}
        if bad:
            return self.warn(metrics=metrics, thresholds=thresholds, reasons=f'{len(bad)}개 운영대상 인터페이스가 up 상태가 아닙니다.', message='운영대상 인터페이스 상태 기준 미달')
        return self.ok(metrics=metrics, thresholds=thresholds, reasons='운영대상 인터페이스가 모두 up 상태입니다.', message='인터페이스 상태 점검이 정상 수행되었습니다.')


CHECK_CLASS = Check
