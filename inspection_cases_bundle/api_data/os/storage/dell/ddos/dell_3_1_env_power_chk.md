# type_name

일상점검

# area_name

상태점검

# category_name

storage

# application_type

dell

# application

ddos

# inspection_code

NETWORK-DELL-DDOS-DELL-3-1-ENV-POWER-CHK

# is_required

권고

# inspection_name

전원공급 장치 점검

# inspection_content

SAN 스위치 SFP 정보 및 상태 확인

# inspection_command

```bash
enclosure show powersupply
```

# inspection_output

```text

```

# description

- enclosure show powersupply 명령어를 통해 스토리지 전원 공급 장치 (Power Supply Module) 상태를 확인할 수 있음
- 각 Enclosure에 장착된 전원 모듈의 정상 동작 여부 및 장애 상태를 점검
- Status 항목을 통해 각 Power Module 상태를 확인하며, 일반적으로 ok 상태일 경우 정상으로 판단

- **양호**: 명령어 출력값에서 모든 Power module 상태가 'ok'로 표시되는 경우 
- **경고**: 명령어 출력값에서 모든 Power module 상태가 'ok'로 표시되지 않는 경우
- **확인 필요**: 명령어 수행 실패 또는 출력 결과를 확인할 수 없는 경우

# thresholds

[]

# inspection_script

# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


COMMAND_ERROR_MARKERS = ('syntax error', 'unknown command', 'invalid command', 'command not found')
COMMAND = 'enclosure show powersupply'
OK_STATUSES = ('ok',)


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'generic_network'
    PARAMIKO_REUSE_SESSION = True

    def _detect_cli_error(self, *texts):
        for text in texts:
            for line in str(text or '').splitlines():
                stripped = line.strip()
                lowered = stripped.lower()
                if stripped and any(marker in lowered for marker in COMMAND_ERROR_MARKERS):
                    return stripped
        return ''

    def _run_command(self):
        results = self._run_paramiko_commands([{'command': COMMAND, 'timeout': 10}], profile=self.PARAMIKO_PROFILE)
        if not results:
            return None, self.fail('점검 명령 실행 실패', message='Paramiko 명령 실행 결과가 비어 있습니다.')
        result = results[0]
        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()
        if result.get('rc') != 0:
            return None, self.fail('점검 명령 실행 실패', message=f'{COMMAND} 명령 실행에 실패했습니다.', stdout=stdout, stderr=stderr)
        error_text = self._detect_cli_error(stdout, stderr)
        if error_text:
            return None, self.fail('점검 명령 실행 실패', message=f'{COMMAND} 명령 출력에서 오류가 확인되었습니다: {error_text}', stdout=stdout, stderr=stderr)
        return stdout, None

    def _parse_power_statuses(self, text):
        statuses = []
        for line in text.splitlines():
            match = re.match(r'^(\d+)\s+(Power module\s+\S+)\s+(\S+)\s*$', line.strip(), re.IGNORECASE)
            if match:
                statuses.append({'enclosure': match.group(1), 'description': match.group(2), 'status': match.group(3)})
        return statuses

    def run(self):
        stdout, error = self._run_command()
        if error:
            return error

        statuses = self._parse_power_statuses(stdout)
        bad_statuses = [item for item in statuses if item['status'].lower() not in OK_STATUSES]
        metrics = {'power_status_count': len(statuses), 'bad_power_statuses': bad_statuses, 'power_statuses': statuses}
        thresholds = {'valid_statuses': list(OK_STATUSES)}
        if not statuses or bad_statuses:
            return self.fail('Power Supply 상태 기준 미달', message='Power module Status가 없거나 OK가 아닌 값이 확인되었습니다.', stdout=stdout, metrics=metrics, thresholds=thresholds)
        return self.ok(metrics=metrics, thresholds=thresholds, reasons='Power module Status가 모두 OK입니다.', message='전원공급 장치 점검 정상.')


CHECK_CLASS = Check
