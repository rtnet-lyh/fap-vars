# type_name

일상점검

# area_name

network

# category_name

상태점검

# application_type

piolink_pas

# application

pas_k3200x

# inspection_code

NETWORK-PIOLINK-PAS-K3200X-ENVIRONMENT-01

# is_required

권고

# inspection_name

전원, FAN 등 점검

# inspection_content

장비의 물리적인 하드웨어(전원, Fan, 라우팅엔진, 라인카드 등) 상태 점검

# inspection_command

```bash
show hardwarestatus
```

# inspection_output

```text

```

# description

- 전원(Power), Fan, Storage 상태 등을 점검
- 장비 내부 센서 기반 HW 상태 확인 가능
- 전원 장애, Fan 이상, 전원장치 이상 여부를 점검

- **양호**: 모든 Power(Voltage) 상태가 'ON'이며, Fan 상태가 'On'이고, Storage 상태가 'Good'인 경우
- **경고**: Power(Voltage) 상태가 'OFF'이거나 Fan 상태가 'OFF'/'FAIL'이거나 Storage 상태가 'Good'이 아닌 경우
- **확인 필요**: 명령어 수행 실패 또는 출력 결과를 확인할 수 없는 경우

# thresholds

[]

# inspection_script

# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


COMMAND = 'show hardwarestatus'
KEY_VALUE_RE = re.compile(r'^\s*(?P<name>[^:]+?)\s*:\s*(?P<value>\S+)')
FAN_RE = re.compile(r'^\s*(?P<name>[A-Za-z0-9 ]+?)\s+(?P<status>ON|OFF|FAIL)\s*$', re.IGNORECASE)


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'generic_network'
    PARAMIKO_REUSE_SESSION = True

    def _run_command(self):
        results = self._run_paramiko_commands([COMMAND], profile=self.PARAMIKO_PROFILE)
        if not results:
            return None, self.fail('점검 명령 실행 실패', message='Paramiko 명령 실행 결과가 비어 있습니다.')
        result = results[0]
        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()
        if result.get('rc') != 0:
            return None, self.fail('점검 명령 실행 실패', message=f'{COMMAND} 명령 실행에 실패했습니다.', stdout=stdout, stderr=stderr)
        return stdout, None

    def _parse_hardware(self, text):
        section = ''
        powers = []
        fans = []
        storage_condition = ''
        for line in (text or '').splitlines():
            stripped = line.strip()
            if stripped in ('Voltage', 'Fan', 'Storage'):
                section = stripped
                continue
            if section == 'Voltage':
                match = KEY_VALUE_RE.match(line)
                if match and match.group('name').strip().lower().startswith('power'):
                    powers.append({'name': match.group('name').strip(), 'status': match.group('value').upper()})
            elif section == 'Fan':
                if stripped.lower().startswith('name '):
                    continue
                match = FAN_RE.match(line)
                if match:
                    fans.append({'name': match.group('name').strip(), 'status': match.group('status').upper()})
            elif section == 'Storage':
                match = KEY_VALUE_RE.match(line)
                if match and match.group('name').strip().lower() == 'condition':
                    storage_condition = match.group('value').strip()
        return powers, fans, storage_condition

    def run(self):
        stdout, error = self._run_command()
        if error:
            return error

        powers, fans, storage_condition = self._parse_hardware(stdout)
        if not powers or not fans or not storage_condition:
            return self.fail('HW 상태 파싱 실패', message='show hardwarestatus 출력에서 Power, Fan, Storage 상태를 모두 찾지 못했습니다.', stdout=stdout, metrics={'power_count': len(powers), 'fan_count': len(fans), 'storage_condition': storage_condition})

        bad_powers = [item for item in powers if item['status'] != 'ON']
        bad_fans = [item for item in fans if item['status'] != 'ON']
        storage_ok = storage_condition.lower() == 'good'
        metrics = {
            'power_count': len(powers),
            'fan_count': len(fans),
            'storage_condition': storage_condition,
            'bad_powers': bad_powers,
            'bad_fans': bad_fans,
            'powers': powers,
            'fans': fans,
        }
        if bad_powers or bad_fans or not storage_ok:
            return self.fail(error="Power, Fan, Storage 중 기준을 만족하지 않는 항목이 있습니다.", metrics=metrics, thresholds={}, reasons='Power, Fan, Storage 중 기준을 만족하지 않는 항목이 있습니다.', message=f'환경 상태 경고: Power {len(bad_powers)}개, Fan {len(bad_fans)}개, Storage={storage_condition}.')
        return self.ok(metrics=metrics, thresholds={}, reasons='Power 상태가 ON, Fan 상태가 ON, Storage 상태가 Good입니다.', message=f'전원/FAN 등 점검 정상: Power {len(powers)}개, Fan {len(fans)}개.')


CHECK_CLASS = Check
