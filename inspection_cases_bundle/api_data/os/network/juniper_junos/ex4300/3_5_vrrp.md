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

NETWORK-JUNIPER-JUNOS-EX4300-3-5-VRRP

# is_required

권고

# inspection_name

이중화 구성 상태 점검

# inspection_content

Failover 상태 확인

# inspection_command

```bash
show vrrp summary
```

# inspection_output

```text

```

# description

- 명령어: VRRP 이중화 그룹 상태를 확인하는 명령어.
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

COMMAND_ERROR_MARKERS = ('syntax error', 'unknown command', 'invalid command', 'unknown keyword', 'missing argument')
COMMAND = 'show vrrp summary'

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

    def run(self):
        stdout, error = self._run_command(COMMAND)
        if error:
            return error

        output_lines = [line.strip() for line in stdout.splitlines() if line.strip()]
        metrics = {'output_line_count': len(output_lines), 'output_lines': output_lines}
        if not output_lines:
            return self.fail('VRRP 상태 기준 미달', message='show vrrp summary 출력이 비어 있습니다.', stdout=stdout, metrics=metrics, thresholds={})
        
        message = 'VRRP 미설정 장비 입니다.' if re.search(r'vrrp subsystem not running', stdout) else '이중화 구성 상태 점검 정상.' # to do 
        return self.ok(metrics=metrics, thresholds={}, reasons=message, message=message)


CHECK_CLASS = Check
