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


NW-JUN-EX4300-002

# is_required

필수

# inspection_name

메모리 사용률

# inspection_content

메모리 사용률 확인

# inspection_command

```bash

```

# inspection_output

```text
falcon@Center_Server_J4300_A> show system memory
fpc0:
--------------------------------------------------------------------------
System memory usage distribution:
       Total memory: 2992128 Kbytes (100%)
    Reserved memory:   59052 Kbytes (  1%)
       Wired memory:  136476 Kbytes (  4%)
      Active memory: 1085592 Kbytes ( 36%)
    Inactive memory:   77940 Kbytes (  2%)
       Cache memory:  584704 Kbytes ( 19%)
        Free memory: 1047824 Kbytes ( 35%)
Memory disk resident memory:  400496 Kbytes
VM-Kbytes(  %  ) Resident(  %  ) Map-name
  1048576(99.99)   944772(90.10) kernel map
   524288(50.00)    48736(09.30) kmem map
     1216(00.12)     1216(99.99) exec map
    26212(02.50)     1092(04.17) pipe map
   115488(11.01)   114784(99.39) buffer map
    32768(03.13)    32768(99.99) pager map
Pid     VM-Kbytes(  %  ) Resident(  %  ) Process-name
      0         0(00.00)        0(00.00) [swapper]
      1         0(00.00)        0(00.00) /sbin/init --
      2         0(00.00)        0(00.00) [jfe_job_0_0]
      3         0(00.00)        0(00.00) [jfe_job_1_0]
---(more)---
```

# description

- 명령어: 시스템 메모리 분포와 사용 현황을 확인하는 명령어.
- Free memory는 현재 사용 가능한 여유량을 의미.
- 메모리 사용률(%) = 100% - Free memory(%)

- **양호**: 메모리 사용률이 `max_mem_usage_percent` 이하인 상태
- **경고**: 메모리 사용률이 `max_mem_usage_percent` 초과인 상태
- **확인 필요**: 명령어 실패 및 파싱 불가

# thresholds

[
    {id: null, key: "max_mem_usage_percent", value: "80", sortOrder: 0}
]

# inspection_script

# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


COMMAND_ERROR_MARKERS = ('syntax error', 'unknown command', 'invalid command', 'unknown keyword', 'missing argument')
COMMAND = 'show system memory'


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

    def _parse_memory_usage(self, text):
        total_match = re.search(r'Total memory:\s*(\d+)\s+Kbytes\s*\(\s*100%\)', text, re.IGNORECASE)
        free_match = re.search(r'Free memory:\s*(\d+)\s+Kbytes\s*\(\s*([0-9.]+)%\s*\)', text, re.IGNORECASE)
        if not total_match or not free_match:
            return None
        free_percent = float(free_match.group(2))
        return {
            'memory_total_kb': int(total_match.group(1)),
            'memory_free_kb': int(free_match.group(1)),
            'memory_free_percent': round(free_percent, 2),
            'memory_usage_percent': round(max(0.0, 100.0 - free_percent), 2),
        }

    def run(self):
        max_usage = self.get_threshold_var('max_mem_usage_percent', default=80.0, value_type='float')
        thresholds = {'max_mem_usage_percent': max_usage}
        stdout, error = self._run_command(COMMAND)
        if error:
            return error

        metrics = self._parse_memory_usage(stdout)
        if not metrics:
            return self.fail('메모리 사용률 파싱 실패', message='메모리 사용률 값을 해석하지 못했습니다.', stdout=stdout, thresholds=thresholds)
        if metrics['memory_usage_percent'] > max_usage:
            return self.fail('메모리 사용률 임계치 초과', message=f'메모리 사용률 {metrics["memory_usage_percent"]}%가 기준 {max_usage}%를 초과했습니다.', stdout=stdout, metrics=metrics, thresholds=thresholds)
        return self.ok(metrics=metrics, thresholds=thresholds, reasons='메모리 사용률이 임계치 이하입니다.', message=f'메모리 사용률 점검 정상: {metrics["memory_usage_percent"]}%.')


CHECK_CLASS = Check
