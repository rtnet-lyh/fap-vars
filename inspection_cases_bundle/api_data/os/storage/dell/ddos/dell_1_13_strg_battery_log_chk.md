# type_name

일상점검

# area_name

storage

# category_name

상태점검

# application_type

dell

# application

ddos

# inspection_code


ST-DELL-DDOS-004

# is_required

필수

# inspection_name

스토리지 Cache 배터리

# inspection_content

배터리 Fault 여부

# inspection_command

```bash
enclosure show nvram
```

# inspection_output

```text

```

# description

- enclosure show nvram 명령어를 통해 Cache Battery(Battery Backup Unit) 오류 및 이상 여부를 확인
- Data Domain OS에서는 일반 스토리지의 Cache Battery 역할을 NVRAM Battery가 수행하며, 전원 장애 발생 시 캐시 데이터 보호 기능을 담당함

- **양호**: 명령어 출력값에서 NVRAM Batteries의 Status 값이 'ok'인 경우
- **경고**: 명령어 출력값에서 NVRAM Batteries의 Status 값이 'ok'가 아닌 경우
- **확인 필요**: 명령어 수행 실패 또는 출력 결과를 확인할 수 없는 경우

# thresholds

[]

# inspection_script

# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


COMMAND_ERROR_MARKERS = ('syntax error', 'unknown command', 'invalid command', 'command not found')
COMMAND = 'enclosure show nvram'
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
        results = self._run_paramiko_commands([COMMAND], profile=self.PARAMIKO_PROFILE)
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

    def _parse_battery_statuses(self, text):
        statuses = []
        in_section = False
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith('NVRAM Batteries'):
                in_section = True
                continue
            if not in_section or not stripped or stripped.startswith(('----', 'Card', 'Status')):
                continue
            if re.match(r'^\d+\s+\d+\s+\S+', stripped):
                parts = stripped.split()
                statuses.append({'card': parts[0], 'battery': parts[1], 'status': parts[2]})
        return statuses

    def run(self):
        stdout, error = self._run_command()
        if error:
            return error

        statuses = self._parse_battery_statuses(stdout)
        bad_statuses = [item for item in statuses if item['status'].lower() not in OK_STATUSES]
        metrics = {'battery_status_count': len(statuses), 'bad_battery_statuses': bad_statuses, 'battery_statuses': statuses}
        thresholds = {'valid_statuses': list(OK_STATUSES)}
        if not statuses or bad_statuses:
            return self.fail('NVRAM Battery 상태 기준 미달', message='NVRAM Battery Status가 없거나 ok가 아닌 값이 확인되었습니다.', stdout=stdout, metrics=metrics, thresholds=thresholds)
        return self.ok(metrics=metrics, thresholds=thresholds, reasons='NVRAM Battery Status가 모두 ok입니다.', message='NVRAM Battery 상태 점검 정상.')


CHECK_CLASS = Check
