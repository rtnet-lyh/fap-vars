# type_name

일상점검

# area_name

network

# category_name

상태점검

# application_type

cisco_ios

# application

c2960x

# inspection_code


NW-CIS-C2960X-004

# is_required

필수

# inspection_name

인터페이스/모듈 상태

# inspection_content

Cisco 장비의 인터페이스/모듈 상태 점검

# inspection_command

```bash
show interface status
```

# inspection_output

```text
[OS: Cisco IOS] 추출된 결과입니다.
C2960X_Service#show interface status

Port      Name               Status       Vlan       Duplex  Speed Type
Gi0/1     ===Service_FW_eth1 connected    99         a-full a-1000 10/100/1000BaseTX
Gi0/2     ===10F===          connected    99         a-full a-1000 10/100/1000BaseTX
Gi0/3     ===B1F===          notconnect   99           auto   auto 10/100/1000BaseTX
Gi0/4                        disabled     1            auto   auto 10/100/1000BaseTX
Gi0/5     ===fileserver_NAS= connected    99         a-full a-1000 10/100/1000BaseTX
Gi0/6                        disabled     99           auto   auto 10/100/1000BaseTX
Gi0/7                        disabled     99           auto   auto 10/100/1000BaseTX
Gi0/8                        disabled     99           auto   auto 10/100/1000BaseTX
Gi0/9                        disabled     99           auto   auto 10/100/1000BaseTX
Gi0/10                       disabled     99           auto   auto 10/100/1000BaseTX
Gi0/11                       disabled     99           auto   auto 10/100/1000BaseTX
Gi0/12                       disabled     99           auto   auto 10/100/1000BaseTX
Gi0/13                       disabled     99           auto   auto 10/100/1000BaseTX
Gi0/14                       disabled     99           auto   auto 10/100/1000BaseTX
Gi0/15                       disabled     99           auto   auto 10/100/1000BaseTX
Gi0/16                       disabled     99           auto   auto 10/100/1000BaseTX
Gi0/17                       disabled     99           auto   auto 10/100/1000BaseTX
Gi0/18                       disabled     99           auto   auto 10/100/1000BaseTX
Gi0/19                       disabled     99           auto   auto 10/100/1000BaseTX
Gi0/20                       disabled     99           auto   auto 10/100/1000BaseTX
Gi0/21                       notconnect   99           auto   auto 10/100/1000BaseTX
Gi0/22                       notconnect   99           auto   auto 10/100/1000BaseTX
Gi0/23                       notconnect   99           auto   auto 10/100/1000BaseTX
Gi0/24                       disabled     99           auto   auto 10/100/1000BaseTX
Gi0/25                       disabled     99           auto   auto Not Present
Gi0/26                       disabled     99           auto   auto Not Present
Fa0       ===MGMT_Fa0/4===   connected    routed     a-full  a-100 10/100BaseTX



---
```

# description

- `show interface status` 명령을 통해 주요 서비스 포트들의 Link Up/Down 상태 및 속도/Duplex 설정을 점검합니다.

- **양호**: 운영에 필요한 모든 인터페이스가 정상적으로 connected 상태임
- **경고**: 주요 인터페이스가 비정상적으로 Down(notconnect) 되거나 속도/Duplex 협상 실패
- **확인 필요**: 명령어 실행 실패, 수집된 출력 결과와 포맷이 다르거나 확인이 불가능한 상태

# thresholds


[]

# inspection_script

# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


COMMAND = 'show interface status'
ROW_RE = re.compile(
    r'^(?P<port>\S+)\s+(?P<name>.*?)(?P<status>connected|notconnect|disabled|err-disabled|inactive|suspended)'
    r'\s+(?P<vlan>\S+)\s+(?P<duplex>\S+)\s+(?P<speed>\S+)\s+(?P<type>.+)$',
    re.IGNORECASE,
)


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'cisco_ios'
    PARAMIKO_REUSE_SESSION = True

    def _set_enable_password(self):
        data = self.get_connection_credential_data()
        for key in ('en_password', 'become_password'):
            value = self.get_connection_value(key, None)
            if value not in (None, ''):
                if isinstance(data, dict) and not data.get('en_password'):
                    data['en_password'] = str(value)
                return True
            value = self.get_application_credential_value(key, None)
            if value not in (None, ''):
                if isinstance(data, dict) and not data.get('en_password'):
                    data['en_password'] = str(value)
                return True
        return False

    def _run_command(self):
        commands = [
            {'command': 'terminal length 0'},
            {'command': COMMAND},
        ]
        results = self._run_paramiko_commands(commands, enable_mode=self._set_enable_password())
        failed = [item for item in results if item.get('rc') != 0]
        if failed:
            first = failed[0]
            command = first.get('display_command') or first.get('command')
            return None, self.fail(
                '점검 명령 실행 실패',
                message=f'{command} 명령 실행에 실패했습니다.',
                stdout=(first.get('stdout') or '').strip(),
                stderr=(first.get('stderr') or '').strip(),
            )
        return (results[-1].get('stdout') or '').strip(), None

    def _parse_rows(self, text):
        rows = []
        for line in (text or '').splitlines():
            match = ROW_RE.match(line.rstrip())
            if not match:
                continue
            rows.append({
                'port': match.group('port'),
                'name': match.group('name').strip(),
                'status': match.group('status').lower(),
                'vlan': match.group('vlan'),
                'duplex': match.group('duplex').lower(),
                'speed': match.group('speed').lower(),
                'type': match.group('type').strip(),
            })
        return rows

    def run(self):
        stdout, error = self._run_command()
        if error:
            return error

        rows = self._parse_rows(stdout)
        if not rows:
            return self.fail(
                '인터페이스 상태 파싱 실패',
                message='show interface status 출력에서 포트 상태를 찾지 못했습니다.',
                stdout=stdout,
            )

        targets = [row for row in rows if row['name']]
        bad = []
        for row in targets:
            negotiated_bad = row['status'] == 'connected' and (
                row['duplex'] in ('auto', 'a-auto') or row['speed'] in ('auto', 'a-auto')
            )
            if row['status'] != 'connected' or negotiated_bad:
                bad.append(row)

        metrics = {
            'interface_count': len(rows),
            'named_interface_count': len(targets),
            'bad_interfaces': bad,
            'named_interfaces': targets,
        }
        if bad:
            return self.warn(
                metrics=metrics,
                thresholds={},
                reasons='이름이 지정된 운영 대상 포트 중 connected 상태가 아닌 포트가 있습니다.',
                message=f'인터페이스 상태 경고: 비정상 운영 대상 포트 {len(bad)}개.',
            )
        return self.ok(
            metrics=metrics,
            thresholds={},
            reasons='이름이 지정된 운영 대상 포트가 모두 connected 상태입니다.',
            message=f'인터페이스 상태 점검 정상: 운영 대상 포트 {len(targets)}개.',
        )


CHECK_CLASS = Check
