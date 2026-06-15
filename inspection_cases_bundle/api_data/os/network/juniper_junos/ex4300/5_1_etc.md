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


NW-JUN-EX4300-013

# is_required

권고

# inspection_name

전원, FAN 등 점검

# inspection_content

장비의 물리적인 하드웨어(전원, FAN, 라우팅엔진, 라인카드 등) 상태 점검

# inspection_command

```bash
show environment
```

# inspection_output

```text
falcon@Center_Server_J4300_B> show chassis environment
Class Item                           Status     Measurement
Power FPC 0 Power Supply 0           OK
      FPC 0 Power Supply 1           OK
Temp  FPC 0 CPU                      OK         50 degrees C / 122 degrees F
      FPC 0 NW-PFE                   OK         40 degrees C / 104 degrees F
      FPC 0 SE-PFE                   OK         35 degrees C / 95 degrees F
      FPC 0 PHY-4/5                  OK         34 degrees C / 93 degrees F
      FPC 0 MGMT PHY                 OK         29 degrees C / 84 degrees F
Fans  FPC 0 Fan 0                    OK         Spinning at normal speed
      FPC 0 Fan 0 Airflow            OK         Airflow Out (AFO)
      FPC 0 Fan 1                    OK         Spinning at normal speed
      FPC 0 Fan 1 Airflow            OK         Airflow Out (AFO)
```

# description

- 명령어: 장비의 물리적인 하드웨어 환경 상태를 확인하는 명령어.

- **양호**: Status 값이 모두 'OK'인 경우
- **경고**: Status 값이 하나라도 'OK'가 아닌 경우
- **확인 필요**: 명령어 실패 및 파싱 실패

# thresholds

[]

# inspection_script

# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


COMMAND_ERROR_MARKERS = ('syntax error', 'unknown command', 'invalid command', 'unknown keyword', 'missing argument')
COMMAND = 'show chassis environment'


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

    def _parse_environment_statuses(self, text):
        statuses = []
        for line in (text or '').splitlines():
            stripped = line.rstrip()
            if not stripped or stripped.startswith('Class ') or set(stripped.strip()) <= {'-'}:
                continue
            match = re.match(r'^\s*(?P<item>.+?)\s{2,}(?P<status>[A-Za-z][A-Za-z_-]*)(?:\s{2,}.*)?$', stripped)
            if not match:
                continue
            status = match.group('status')
            if status.lower() not in ('status', 'measurement'):
                statuses.append({'item': match.group('item').strip(), 'status': status})
        return statuses

    def run(self):
        stdout, error = self._run_command(COMMAND)
        if error:
            return error

        statuses = self._parse_environment_statuses(stdout)
        if not statuses:
            return self.fail('환경 상태 파싱 실패', message='show chassis environment 출력에서 Status 값을 찾지 못했습니다.', stdout=stdout, thresholds={})
        bad_statuses = [item for item in statuses if item['status'].upper() != 'OK']
        metrics = {'status_count': len(statuses), 'bad_statuses': bad_statuses, 'statuses': statuses}
        if bad_statuses:
            return self.fail('환경 상태 기준 미달', message=f'OK가 아닌 하드웨어 Status가 {len(bad_statuses)}개 있습니다.', stdout=stdout, metrics=metrics, thresholds={})
        return self.ok(metrics=metrics, thresholds={}, reasons='하드웨어 Status 값이 모두 OK입니다.', message='전원/FAN 등 환경 상태 점검 정상.')


CHECK_CLASS = Check
