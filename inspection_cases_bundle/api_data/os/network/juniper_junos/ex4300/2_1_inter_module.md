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


NW-JUN-EX4300-004

# is_required

필수

# inspection_name

인터페이스/모듈 상태

# inspection_content

인터페이스/모듈의 Down/Up 상태 점검

# inspection_command

```bash
show interfaces terse
```

# inspection_output

```text
falcon@Center_Server_J4300_A> show interfaces terse
Interface               Admin Link Proto    Local                 Remote
ge-0/0/0                up    up
ge-0/0/0.0              up    up   eth-switch
gr-0/0/0                up    up
pfe-0/0/0               up    up
pfe-0/0/0.16383         up    up   inet
                                   inet6
pfh-0/0/0               up    up
pfh-0/0/0.16383         up    up   inet
pfh-0/0/0.16384         up    up   inet
ge-0/0/1                up    up
ge-0/0/1.0              up    up   eth-switch
me0                     down  down
me0.0                   up    down eth-switch
mtun                    up    up
pimd                    up    up
pime                    up    up
tap                     up    up
vme                     up    down
vme.0                   up    down inet
```

# description

- 명령어: 인터페이스 상태를 요약하여 확인하는 명령어.
- admin: 관리상태를 의미, up이면 설정상 활성화 된 상태이고 down 이면 관리적으로 비활성화 된 상태임.
- Link: 물리 링크 상태를 의미, up이면 정상 연결이고 down 이면 링크가 내려간 상태임. 

[참고]
- 운영대상 인터페이스를 변수로 설정하는것이 옳아보이나, 많은 변수를 선언해야하는 문제가 있음
- 운영 대상 목록 없이 자동화 시 admin up + link down만 취약처리.

- **양호**: admin이 down이거나 admin이 up이고 link가 up인 경우
- **경고**: admin이 up이고 link가 down인 경우
- **확인 필요**: 명령어 실패 및 파싱 불가

# thresholds

[]

# inspection_script

# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


COMMAND_ERROR_MARKERS = ('syntax error', 'unknown command', 'invalid command', 'unknown keyword', 'missing argument')
COMMAND = 'show interfaces terse'


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

    def _parse_interface_states(self, text):
        rows = []
        for line in (text or '').splitlines():
            match = re.match(r'^(\S+)\s+(up|down)\s+(up|down)(?:\s|$)', line.strip(), re.IGNORECASE)
            if match:
                rows.append({'interface': match.group(1), 'admin': match.group(2).lower(), 'link': match.group(3).lower()})
        return rows

    def run(self):
        stdout, error = self._run_command(COMMAND)
        if error:
            return error

        interfaces = self._parse_interface_states(stdout)
        if not interfaces:
            return self.fail('인터페이스 상태 파싱 실패', message='show interfaces terse 출력에서 인터페이스 상태 행을 찾지 못했습니다.', stdout=stdout)
        bad_interfaces = [item for item in interfaces if item['admin'] == 'up' and item['link'] != 'up']
        metrics = {
            'interface_count': len(interfaces),
            'bad_interface_count': len(bad_interfaces),
            'bad_interfaces': bad_interfaces,
            'interfaces': interfaces,
        }
        if bad_interfaces:
            return self.fail('인터페이스 상태 기준 미달', message=f'admin up/link down 인터페이스가 {len(bad_interfaces)}개 있습니다.', stdout=stdout, metrics=metrics, thresholds={})
        return self.ok(metrics=metrics, thresholds={}, reasons='admin up 인터페이스의 link가 모두 up입니다.', message='인터페이스/모듈 상태 점검 정상.')


CHECK_CLASS = Check
