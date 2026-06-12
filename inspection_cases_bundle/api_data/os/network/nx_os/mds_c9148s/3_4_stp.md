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

NETWORK-NXOS-MDS-C9148S-STP-01

# is_required

권고

# inspection_name

STP 상태 점검

# inspection_content

STP 설정을 통해 Loop 구조를 방지하고 원활한 통신상태를 확인

# inspection_command

```bash
show spannig-tree
```

# inspection_output

```text
CITS-SAN1# show spannig-tree
                    ^
% Invalid command at '^' marker.
```

# description

- 명령어: Loop를 방지를 확인하는 명령어.
- Cisco SAN 장비에는 Fibre Channel Fabric 기반으로 동작하므로 Ethernet L2 스위치의 STP를 사용하지 않음.

- **양호**: 점검 대상이 아님.
- **경고**: 점검 대상이 아님.
- **확인 필요**: 점검 대상이 아님.

# thresholds

[]

# inspection_script

# -*- coding: utf-8 -*-

from .common._base import BaseCheck


class Check(BaseCheck):
    USE_HOST_CONNECTION = False

    def run(self):
        return self.ok(
            metrics={'applicable': False},
            thresholds={},
            reasons='해당 장비는 Ethernet STP 점검 대상이 아닙니다.',
            message='점검 대상이 아닙니다.',
        )


CHECK_CLASS = Check
