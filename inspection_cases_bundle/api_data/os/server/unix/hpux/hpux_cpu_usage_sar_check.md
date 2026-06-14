# type_name

일상점검

# area_name

server

# category_name

상태점검

# application_type

unix

# application

hpux

# inspection_code

HPUX-REPLAY-CPU-01

# is_required

필수

# inspection_name

CPU 사용률

# inspection_content

CPU 사용률 점검

# inspection_command

```bash
sar -u 1 3
```

# inspection_output

```text
HP-UX hpux01 B.11.31 U ia64  12/30/25

12:10:01  %usr  %sys  %wio  %idle
12:10:02     8     7     1     84
12:10:03    14     9     2     75
Average     11     8     1     80
```

# description

- `sar -u 1 3` 명령으로 HP-UX 시스템의 CPU 사용률을 1초 간격으로 3회 확인한다.
- CPU 사용률은 `100 - %idle`로 산정한다.
- 마지막 샘플 또는 평균값 기준으로 사용률이 높으면 CPU 병목, 과다 프로세스, 배치 작업 집중 여부를 확인한다.
- 명령 실행 불가, 권한 문제, 출력 파싱 실패 시에는 확인 필요로 분류한다.

- **양호**: CPU 사용률이 `CPU_MAX_PCT` 이하인 경우
- **경고**: CPU 사용률이 `CPU_MAX_PCT`를 초과하는 경우
- **확인 필요**: `sar` 명령 실행 또는 결과 해석이 불가능한 경우

# thresholds

[
    {id: null, key: "CPU_MAX_PCT", value: "70", sortOrder: 0}
]

# inspection_script

# -*- coding: utf-8 -*-

import re
import time

from .common._base import BaseCheck

CHECK_COMMAND = 'sar -u 1 3'
BECOME_COMMAND_TIMEOUT = 1

class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_AUTH_TIMEOUT_SEC = 30
    
    def _is_become_enabled(self):
        value = self.get_connection_value('become', default=False)
        return str(value).strip().lower() in ('1', 'true', 'y', 'yes', 'on')

    def _build_become_command(self):
        if not self._is_become_enabled():
            return ''

        method = str(self.get_connection_value('become_method', default='su -') or 'su -')
        method = ' '.join(method.strip().lower().split())
        user = str(self.get_connection_value('become_user', default='root') or 'root').strip() or 'root'

        if method == 'su':
            return 'su ' + user
        if method == 'su -':
            return 'su - ' + user
        if method == 'sudo':
            return 'sudo -u ' + user + ' -i'
        raise ValueError(f'unsupported become_method: {method}')

    def _build_check_command(self, become_command):

        if become_command:
            become_password = self.get_connection_value('become_password', default='')    
            return [
                {
                    'command': become_command,
                    'timeout': BECOME_COMMAND_TIMEOUT,
                    'ignore_prompt': True,                    
                },
                {
                    'command': become_password,
                    'hide_command': True,
                },
                {
                    'command': CHECK_COMMAND,
                }
            ]
        else:
            return [{'command': CHECK_COMMAND}]

    def _find_check_result(self, results):
        for item in reversed(results):
            if item.get('command') == CHECK_COMMAND:
                return item
        return None

    def _parse_hpux_cpu_usage(self, output: str):
        # VMS2:root[/]# sar -u 1 5

        # HP-UX VMS2 B.11.31 U ia64    05/08/26

        # 10:32:24    %usr    %sys    %wio   %idle
        # 10:32:25       0       1       0      99
        # 10:32:26       0       0       0     100
        # 10:32:27       0       0       0     100
        # 10:32:28       1       1       0     100
        # 10:32:29       0       0       0      99

        # Average        0       0       0     100

        results = {}

        match = re.search(r"Average\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)", output)        
        if match:
            results["user"] = float(match.group(1))
            results["sys"] = float(match.group(2))
            results["wio"] = float(match.group(3))
            results["idle"] = float(match.group(4))
            results["cpu_usage"] = 100 - results["idle"]

        return results

    def run(self):
        try:

            become_command = self._build_become_command()
            commands = self._build_check_command(become_command)

            results = self._run_paramiko_commands(commands)
            result = self._find_check_result(results)

            metrics = {}

            max_cpu_usage = self.get_threshold_var(key='MAX_CPU_USAGE', default=80, value_type='int')

            if result is None:
                failed_result = next((item for item in results if item.get('rc') != 0), None)
                return self.fail(
                    error='명령 결과 없음',
                    message='명령 실행 결과를 찾지 못했습니다.',
                    stdout=(failed_result.get('stdout') or '').strip() if failed_result else '',
                    stderr=(failed_result.get('stderr') or '').strip() if failed_result else '',
                    metrics={
                        'executed_commands': [
                            item.get('display_command') or item.get('command')
                            for item in results
                        ],
                    },
                )

            output = result.get('stdout', '')            
            parsed = self._parse_hpux_cpu_usage(output=output)                                              
            metrics = parsed 
            if parsed:                     
                user = parsed.get("user")  
                sys = parsed.get("sys")  
                wio = parsed.get("wio")  
                idle = parsed.get("idle")  
                cpu_usage = parsed.get("cpu_usage")                                 
                
                is_pass = True if cpu_usage < max_cpu_usage else False                    
                
                if is_pass:
                    return self.ok(
                        metrics = metrics,
                        reasons = f"CPU 사용률이 정상입니다. 임계치: {max_cpu_usage}% / 사용률: {cpu_usage}%",
                        message = f"CPU 사용률이 정상입니다. 임계치: {max_cpu_usage}% / 사용률: {cpu_usage}%",
                    )
                else:
                    return self.fail(
                        error="CPU 사용률 임계치 초과",                        
                        message=f"CPU 사용률 임계치 초과. 임계치: {max_cpu_usage}% / 사용률: {cpu_usage}%",
                    )
            else:
                return self.fail(
                    error="CPU 사용률 점검 실패",
                    message=f"CPU 사용률 점검 실패: {parsed}",                
                )

        except Exception as e:
            import traceback

            return self.fail(
                error=f"CPU 사용률 점검 실패: {str(traceback.print_exc())}",
                message=f"CPU 사용률 점검 실패: {str(traceback.print_exc())}",                
            )

CHECK_CLASS = Check
