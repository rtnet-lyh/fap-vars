# type_name

일상점검

# area_name

network

# category_name

상태점검

# application_type

juniper_junos

# application

ex4300

# inspection_code

NETWORK-JUNIPER-JUNOS-EX4300-3-2-MAC

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
falcon@Center_Server_J4300_A> show arp
MAC Address       Address         Name                      Interface               Flags
40:5b:7f:6d:53:60 172.18.8.191    172.18.8.191              irb.808 [ge-0/0/28.0]   none
44:8a:5b:dc:44:02 172.18.8.230    172.18.8.230              irb.808 [xe-0/0/35.0]   none
00:06:c4:90:0d:53 172.18.8.252    172.18.8.252              irb.808 [ge-0/0/28.0]   none
00:00:5e:00:01:fe 172.18.8.254    172.18.8.254              irb.808 [ge-0/0/28.0]   none
Total entries: 4
```

# description

- 명령어: arp 테이블(IP와 MAC 주소간의 매핑정보 저장 테이블) 정보를 확인하는 명령어.

[참고]
- CISCO 장비와 동일함
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


COMMAND_ERROR_MARKERS = ('syntax error', 'unknown command', 'invalid command', 'unknown keyword', 'missing argument')
COMMAND = 'show arp'
MAC_RE = re.compile(r'^[0-9a-f]{2}(?::[0-9a-f]{2}){5}$', re.IGNORECASE)
IP_RE = re.compile(r'^\d+(?:\.\d+){3}$')


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'generic_network'
    PARAMIKO_REUSE_SESSION = True

    def _run_command(self, command):
        results = self._run_paramiko_commands([command], profile=self.PARAMIKO_PROFILE)
        if not results:
            return None, self.fail('점검 명령 실행 실패', message='Paramiko 명령 실행 결과가 비어 있습니다.')
        result = results[0]
        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()
        if result.get('rc') != 0:
            return None, self.fail('점검 명령 실행 실패', message=f'{command} 명령 실행에 실패했습니다.', stdout=stdout, stderr=stderr)
        error_text = self._detect_cli_error(stdout, stderr)
        if error_text:
            return None, self.fail('점검 명령 실행 실패', message=f'{command} 명령 출력에서 오류가 확인되었습니다: {error_text}', stdout=stdout, stderr=stderr)
        return stdout, None

    def _detect_cli_error(self, *texts):
        for text in texts:
            for line in str(text or '').splitlines():
                stripped = line.strip()
                lowered = stripped.lower()
                if stripped and any(marker in lowered for marker in COMMAND_ERROR_MARKERS):
                    return stripped
        return ''

    def _parse_arp_entries(self, text):
        entries = []
        for line in (text or '').splitlines():
            parts = line.split()
            if len(parts) >= 4 and MAC_RE.match(parts[0]) and IP_RE.match(parts[1]):
                entries.append({'mac_address': parts[0], 'ip_address': parts[1], 'name': parts[2], 'interface': parts[4]})
        return entries

    def run(self):
        stdout, error = self._run_command(COMMAND)
        if error:
            return error

        entries = self._parse_arp_entries(stdout)
        metrics = {'arp_entry_count': len(entries), 'arp_entries': entries}
        if not entries:
            return self.fail('MAC/ARP 파싱 실패', message='show arp 출력에서 MAC/IP/interface 행을 찾지 못했습니다.', stdout=stdout, metrics=metrics, thresholds={})
        return self.ok(metrics=metrics, thresholds={}, reasons='MAC/IP/interface 행이 1개 이상 정상 파싱되었습니다.', message=f'MAC/ARP 테이블 점검 정상: {len(entries)}개 항목.')


CHECK_CLASS = Check
