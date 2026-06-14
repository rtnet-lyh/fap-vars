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

NETWORK-JUNIPER-JUNOS-EX4300-1-1-CPU

# is_required

필수

# inspection_name

CPU 사용률

# inspection_content

CPU 자원 사용률 확인

# inspection_command

```bash
show chassis routing-engine
```

# inspection_output

```text
falcon@Center_Server_J4300_A> show chassis routing-engine
Routing Engine status:
  Slot 0:
    Current state                  Master
    Temperature                 48 degrees C / 118 degrees F
    CPU temperature             48 degrees C / 118 degrees F
    DRAM                      3072 MB
    Memory utilization          48 percent
    5 sec CPU utilization:
      User                       6 percent
      Background                 0 percent
      Kernel                     3 percent
      Interrupt                  0 percent
      Idle                      91 percent
    Model                          EX4300-32F
    Serial ID                      TW3720310093
    Start time                     2020-11-12 07:19:14 KST
    Uptime                         2023 days, 13 hours, 54 minutes, 30 seconds
    Last reboot reason             0x1:power cycle/failure
    Load averages:                 1 minute   5 minute  15 minute
                                       0.15       0.16       0.10
```

# description

- 명령어: 라우팅 엔진 상태를 확인하는 명령어.
- 5 sec CPU utilization의 Idle 값은 사용되지 않고 남아있는 CPU의 비율을 의미함.
- CPU사용률: 100 - Idle

- **양호**: CPU 사용률이 `max_cpu_usage_percent` 이하인 상태
- **경고**: CPU 사용률이 `max_cpu_usage_percent` 초과인 상태
- **확인 필요**: 명령어 실패 및 파싱 불가.

# thresholds

[
    {id: null, key: "max_cpu_usage_percent", value: "80", sortOrder: 0}
]

# inspection_script

# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


COMMAND_ERROR_MARKERS = ('syntax error', 'unknown command', 'invalid command', 'unknown keyword', 'missing argument')
COMMAND = 'show chassis routing-engine'


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

    def _parse_cpu_usage(self, text):
        idle_match = re.search(r'\bIdle\s+([0-9.]+)\s+percent', text, re.IGNORECASE)
        if idle_match:
            idle_percent = float(idle_match.group(1))
            return {
                'idle_percent': round(idle_percent, 2),
                'cpu_usage_percent': round(max(0.0, 100.0 - idle_percent), 2),
            }

        values = []
        for name in ('User', 'Background', 'Kernel', 'Interrupt'):
            match = re.search(r'\b' + name + r'\s+([0-9.]+)\s+percent', text, re.IGNORECASE)
            if match:
                values.append(float(match.group(1)))
        if not values:
            return None
        return {'cpu_usage_percent': round(sum(values), 2)}

    def run(self):
        max_usage = self.get_threshold_var('max_cpu_usage_percent', default=80.0, value_type='float')
        thresholds = {'max_cpu_usage_percent': max_usage}
        stdout, error = self._run_command(COMMAND)
        if error:
            return error

        metrics = self._parse_cpu_usage(stdout)
        if not metrics:
            return self.fail('CPU 사용률 파싱 실패', message='CPU 사용률 값을 해석하지 못했습니다.', stdout=stdout, thresholds=thresholds)
        if metrics['cpu_usage_percent'] > max_usage:
            return self.fail('CPU 사용률 임계치 초과', message=f'CPU 사용률 {metrics["cpu_usage_percent"]}%가 기준 {max_usage}%를 초과했습니다.', stdout=stdout, metrics=metrics, thresholds=thresholds)
        return self.ok(metrics=metrics, thresholds=thresholds, reasons='CPU 사용률이 임계치 이하입니다.', message=f'CPU 사용률 점검 정상: {metrics["cpu_usage_percent"]}%.')


CHECK_CLASS = Check
