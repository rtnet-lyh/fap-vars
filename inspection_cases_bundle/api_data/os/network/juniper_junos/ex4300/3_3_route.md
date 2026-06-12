# type_name

일상점검

# area_name

상태점검

# category_name

network

# application_type

juniper_junos

# application

ex4300

# inspection_code

NETWORK-JUNIPER-JUNOS-EX4300-3-3-ROUTE

# is_required

권고

# inspection_name

라우팅 Table 상태

# inspection_content

라우팅 Table 정상 여부 확인

# inspection_command

```bash
show route 0.0.0.0
```

# inspection_output

```text

```

# description

- 명령어: IP 라우팅 테이블 상태를 확인하는 명령어
- Default Route가 목적지 경로를 찾지 못할 때 트래픽을 전송할 경로인 기본 gateway인 0.0.0.0으로 설정되어있어야함.

- **양호**: 결과 값 내 '0.0.0.0' 문구 존재
- **경고**: 결과 값 내 '0.0.0.0' 문구 미 존재
- **확인 필요**: 명령어 실패 및 파싱 불가

# thresholds

[]

# inspection_script

# -*- coding: utf-8 -*-

from .common._base import BaseCheck


COMMAND_ERROR_MARKERS = ('syntax error', 'unknown command', 'invalid command', 'unknown keyword', 'missing argument')
COMMAND = 'show route 0.0.0.0'


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

        has_default_route = '0.0.0.0' in stdout
        metrics = {'has_default_route': has_default_route}
        if not has_default_route:
            return self.fail('라우팅 상태 기준 미달', message='출력에서 0.0.0.0 경로를 찾지 못했습니다.', stdout=stdout, metrics=metrics, thresholds={})
        return self.ok(metrics=metrics, thresholds={}, reasons='출력에서 0.0.0.0 경로가 확인되었습니다.', message='라우팅 Table 상태 점검 정상.')


CHECK_CLASS = Check
