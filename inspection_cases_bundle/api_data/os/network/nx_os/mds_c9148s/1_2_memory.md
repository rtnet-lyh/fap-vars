# type_name

일상점검

# area_name

network

# category_name

상태점검

# application_type

nx_os

# application

mds_c9148s

# inspection_code


NW-NX-MDS9148-002

# is_required

필수

# inspection_name

메모리 사용률

# inspection_content

전체 메모리 크키 확인 및 사용량과 여유메모리 확인(여유메모리 10%권고)

# inspection_command

```bash
show system resources
```

# inspection_output

```text
CITS-SAN1# show system resources
Load average:   1 minute: 0.14   5 minutes: 0.15   15 minutes: 0.16
Processes   :   181 total, 1 running
CPU states  :   2.48% user,   4.47% kernel,   93.03% idle
        CPU0 states  :   2.00% user,   2.00% kernel,   96.00% idle
        CPU1 states  :   2.97% user,   6.93% kernel,   90.09% idle
Memory usage:   4155776K total,   795688K used,   3360088K free
Current memory status: OK
```

# description

- 명령어: CPU, 프로세스, 메모리 등 시스템 자원 사용상태 확인 명령어
- 'Memory usage:' 항목에서 전체 메모리 용량, 사용 중인 메모리, 여유 메모리를 확인 할 수 있음.
- 메모리 사용률(%) = used / total * 100

- **양호**: 메모리 사용률이 `max_mem_usage_percent` 이하인 상태
- **경고**: 메모리 사용률이 `max_mem_usage_percent` 초과인 상태
- **확인 필요**: 명령어 실패 및 'Memory usage:' 파싱 불가, Current memory status: OK가 아닌 경우.

# thresholds

[
    {id: null, key: "max_mem_usage_percent", value: "90", sortOrder: 0}
]

# inspection_script

# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


COMMAND = 'show system resources'
MEMORY_RE = re.compile(r'Memory usage:\s*(\d+)K total,\s*(\d+)K used,\s*(\d+)K free')
STATUS_RE = re.compile(r'Current memory status:\s*(\S+)', re.IGNORECASE)


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'
    SSH_CONTROL_MASTER = False
    
    def run(self):
        max_usage = self.get_threshold_var('max_mem_usage_percent', default=90.0, value_type='float')
        thresholds = {'max_mem_usage_percent': max_usage}
        rc, out, err = self._ssh(COMMAND)
        if rc != 0:
            return self.fail('점검 명령 실행 실패', message=f'{COMMAND} 명령 실행에 실패했습니다.', stdout=(out or '').strip(), stderr=(err or '').strip(), thresholds=thresholds)

        text = (out or '').strip()
        memory = MEMORY_RE.search(text)
        status = STATUS_RE.search(text)
        if not memory or not status:
            return self.fail('메모리 사용률 파싱 실패', message='Memory usage 또는 Current memory status 값을 해석하지 못했습니다.', stdout=text, thresholds=thresholds)

        total_kb, used_kb, free_kb = [int(memory.group(i)) for i in (1, 2, 3)]
        usage = round(used_kb / total_kb * 100, 2) if total_kb else 0.0
        metrics = {
            'memory_total_kb': total_kb,
            'memory_used_kb': used_kb,
            'memory_free_kb': free_kb,
            'memory_usage_percent': usage,
            'current_memory_status': status.group(1),
        }
        if status.group(1).upper() != 'OK':
            return self.warn(metrics=metrics, thresholds=thresholds, reasons='Current memory status가 OK가 아닙니다.', message=f'Current memory status={status.group(1)}')
        if usage > max_usage:
            return self.warn(metrics=metrics, thresholds=thresholds, reasons=f'메모리 사용률 {usage}%가 임계치 {max_usage}%를 초과했습니다.', message=f'메모리 사용률 기준 초과: {usage}%')
        return self.ok(metrics=metrics, thresholds=thresholds, reasons=f'메모리 사용률 {usage}%가 임계치 {max_usage}% 이하입니다.', message=f'메모리 사용률 점검이 정상 수행되었습니다. usage={usage}%.')


CHECK_CLASS = Check
