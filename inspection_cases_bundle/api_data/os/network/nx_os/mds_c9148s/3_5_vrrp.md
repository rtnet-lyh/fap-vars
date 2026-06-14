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

NETWORK-NXOS-MDS-C9148S-VRRP-01

# is_required

권고

# inspection_name

이중화 구성 상태 점검

# inspection_content

이중화 구성 상태 확인

# inspection_command

```bash
show vrrp
```

# inspection_output

```text

```

# description

- 명령어: VRRP 상태를 확인하는 명령어.
- 이중화 구성이 되어있는 장비가 없어 결과 확인 불가.

[참고]
- 이중화 구성이 되어있더라도 master 장비와 slave 장비의 각각 state 값과 addr 값을 비교해야함. (가이드참고)

- **양호**: 명령어 결과 있음
- **경고**: 명령어 결과 없음
- **확인 필요**:

# thresholds

[]

# inspection_script

# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


COMMAND = 'show vrrp'
PROMPT_RE = re.compile(r'^[A-Za-z0-9_.:/-]+[>#]\s*$')


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'
    SSH_CONTROL_MASTER = False

    def _data_lines(self, text):
        lines = []
        for line in (text or '').splitlines():
            stripped = line.strip()
            if not stripped or PROMPT_RE.match(stripped) or stripped.endswith('# ' + COMMAND):
                continue
            lines.append(stripped)
        return lines

    def run(self):
        rc, out, err = self._ssh(COMMAND)
        if rc != 0:
            return self.fail('점검 명령 실행 실패', message=f'{COMMAND} 명령 실행에 실패했습니다.', stdout=(out or '').strip(), stderr=(err or '').strip())

        lines = self._data_lines(out)
        metrics = {'vrrp_line_count': len(lines), 'vrrp_lines': lines}
        if not lines:
            return self.warn(metrics=metrics, thresholds={}, reasons='VRRP 명령 결과가 없습니다.', message='VRRP 구성 또는 결과가 확인되지 않았습니다.')
        return self.ok(metrics=metrics, thresholds={}, reasons='VRRP 명령 결과가 확인되었습니다.', message='VRRP 상태 점검이 정상 수행되었습니다.')


CHECK_CLASS = Check
