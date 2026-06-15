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


NW-NX-MDS9148-007

# is_required

권고

# inspection_name

MAC/Arp Table 상태 확인

# inspection_content

MAC/Arp Table 정상 여부 확인

# inspection_command

```bash
show arp
```

# inspection_output

```text
CITS-SAN1# show arp
Protocol Address         Age (min) Hardware Addr                 Type Interface
Internet 193.1.0.254     0         0000.0c07.acc1                ARPA mgmt0
```

# description

- 명령어: arp 테이블(IP와 MAC 주소간의 매핑정보 저장 테이블) 정보를 확인하는 명령어.

[참고]
- IP와 MAC 이 정상적으로 매핑이 되는지 확인하는 항목. 어떤 값이 정상 값인지 판단 힘듦
1안. Hardware Addr과 Interface가 정상적으로 출력 되면 양호처리.
2안. 정상인 IP와 MAC 값을 변수로 받아 일치하면 양호처리.
3안. 출력만 하고 담당자 확인처리.

- **양호**: 참고를 참고하세요 .. 
- **경고**: 
- **확인 필요**:

# thresholds

[]

# inspection_script

# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


COMMAND = 'show arp'
ARP_RE = re.compile(r'^\S+\s+(?P<ip>\d+(?:\.\d+){3})\s+\S+\s+(?P<mac>[0-9a-f.]+)\s+\S+\s+(?P<interface>\S+)', re.IGNORECASE)


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'
    SSH_CONTROL_MASTER = False

    def run(self):
        rc, out, err = self._ssh(COMMAND)
        if rc != 0:
            return self.fail('점검 명령 실행 실패', message=f'{COMMAND} 명령 실행에 실패했습니다.', stdout=(out or '').strip(), stderr=(err or '').strip())

        entries = [m.groupdict() for m in (ARP_RE.match(line.strip()) for line in (out or '').splitlines()) if m]
        metrics = {'arp_entry_count': len(entries), 'arp_entries': entries}
        if not entries:
            return self.fail('ARP 테이블 파싱 실패', message='Hardware Addr와 Interface가 있는 ARP 항목을 찾지 못했습니다.', stdout=(out or '').strip(), metrics=metrics)
        return self.ok(metrics=metrics, thresholds={}, reasons='Hardware Addr와 Interface가 있는 ARP 항목이 확인되었습니다.', message=f'ARP 테이블 점검이 정상 수행되었습니다. entries={len(entries)}.')


CHECK_CLASS = Check
