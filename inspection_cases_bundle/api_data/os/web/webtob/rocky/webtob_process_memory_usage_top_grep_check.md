# type_name

일상점검

# area_name

상태점검

# category_name

web

# application_type

webtob

# application

rocky

# inspection_code

WEBTOB-ROCKY-REPLAY-005

# is_required

필수

# inspection_name

프로세스 메모리 사용률

# inspection_content

WEB 서비스 부하 확인을 위한 WEB 프로세스가 사용하고 있는 메모리 자원 사용률 확인

# inspection_command

```bash
- process_name 변수 
```bash
top -b -n 1 | egrep "PID|{{ process_name }}" # 헤더 포함
```
```bash
top -b -n 1 | grep -E "{{ process_name }}" # 헤더 미포함
```
```

# inspection_output

```text
[root@sd_tipswebwas ~]# top -b -n 1 | egrep "PID|exTMS"
    PID USER      PR  NI    VIRT    RES    SHR S  %CPU  %MEM     TIME+ COMMAND
   4937 exTMS     20   0   89776   5716   4184 S   0.0   0.0   2:46.91 systemd
   4940 exTMS     20   0  301032   5496      0 S   0.0   0.0   0:00.00 (sd-pam)
   5029 exTMS     20   0   64484   3180   2680 S   0.0   0.0   0:00.00 dbus-daemon
1476176 exTMS     20   0 6052980 940596  30104 S   0.0   5.8  93:31.63 java
1480138 exTMS     20   0   19032   8728   8536 S   0.0   0.1   8:27.12 wsm
1480139 exTMS     20   0   12588    900    828 S   0.0   0.0   2:40.03 htl
1480140 exTMS     20   0 1211928 596944  10828 S   0.0   3.7   3:13.83 hth
3485909 exTMS     20   0  243244   6392   2628 S   0.0   0.0   0:12.54 tmux: server
3485910 exTMS     20   0  226432   4840   2716 S   0.0   0.0   0:00.01 bash
```

# description

- %MEM: 메모리 사용률이 높을 경우 성능 저하가 발생할 수 있으므로 모니터링 및 메모리 추가, 최적화 작업이 필요.

- **양호**: 메모리 사용률이 `max_mem_usage_percent` 이하인 상태
- **경고**: 메모리 사용률이 `max_mem_usage_percent`를 초과한 상태
- **확인 필요**: 대상 프로세스가 없거나 top 출력에서 대상 프로세스를 찾지 못하는 상태

# thresholds

[
    {id: null, key: "process_name", value: "exTMS", sortOrder: 0}
,
{id: null, key: "max_mem_usage_percent", value: "70", sortOrder: 1}
]

# inspection_script

# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'linux'
    PARAMIKO_REUSE_SESSION = False

    DEFAULT_PROCESS_NAME = 'exTMS'
    DEFAULT_MAX_MEM_USAGE_PERCENT = 70.0
    COMMAND_TIMEOUT = 10

    def _parse_top_rows(self, stdout):
        header = []
        rows = []
        for line in str(stdout or '').splitlines():
            parts = re.split(r'\s+', line.strip())
            if not parts or parts == ['']:
                continue
            if 'PID' in parts and '%CPU' in parts and '%MEM' in parts:
                header = parts
                continue
            if not header or len(parts) < len(header):
                continue

            try:
                row = {
                    'pid': parts[header.index('PID')],
                    'user': parts[header.index('USER')],
                    'state': parts[header.index('S')],
                    'cpu_percent': float(parts[header.index('%CPU')]),
                    'mem_percent': float(parts[header.index('%MEM')]),
                    'command': parts[header.index('COMMAND')],
                }
            except (ValueError, IndexError):
                continue
            rows.append(row)
        return rows

    def run(self):
        proccess_name = self.get_host_var(key='process_name')
        if not proccess_name:
            process_name = self.get_threshold_var(
                'process_name', 
                default=self.DEFAULT_PROCESS_NAME, 
                value_type='str'
            ).strip() 

        max_mem_usage_percent = self.get_threshold_var(
            'max_mem_usage_percent',
            default=self.DEFAULT_MAX_MEM_USAGE_PERCENT,
            value_type='float',
        )
        command = 'top -b -n 1 | egrep "PID|%s"' % process_name

        result = self._run_paramiko_commands(
            [{'command': command, 'timeout': self.COMMAND_TIMEOUT}],
            become=True,
            profile='linux',
        )[0]

        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()
        if result.get('rc') != 0:
            return self.fail(
                'top 명령 실행 실패',
                message='WEB 프로세스 메모리 사용률을 확인하지 못했습니다.',
                stdout=stdout,
                stderr=stderr,
            )

        rows = self._parse_top_rows(stdout)
        if not rows:
            return self.fail(
                '프로세스 정보 없음',
                message='top 출력에서 대상 프로세스를 찾지 못했습니다.',
                stdout=stdout,
                stderr=stderr,
            )

        max_row = max(rows, key=lambda row: row['mem_percent'])
        over_rows = [row for row in rows if row['mem_percent'] > max_mem_usage_percent]
        metrics = {
            'process_name': process_name,
            'process_count': len(rows),
            'max_mem_usage_percent': max_row['mem_percent'],
            'max_mem_pid': max_row['pid'],
            'max_mem_command': max_row['command'],
            'over_threshold_count': len(over_rows),
            'processes': rows,
        }
        thresholds = {
            'process_name': process_name,
            'max_mem_usage_percent': max_mem_usage_percent,
        }

        if over_rows:
            return self.warn(
                metrics=metrics,
                thresholds=thresholds,
                reasons='메모리 사용률 기준 초과 프로세스가 있습니다.',
                message='WEB 프로세스 메모리 사용률 경고: 최대 %.1f%%, 기준 %.1f%%' % (
                    max_row['mem_percent'],
                    max_mem_usage_percent,
                ),
            )

        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='대상 프로세스 메모리 사용률이 기준 이하입니다.',
            message='WEB 프로세스 메모리 사용률 정상: 최대 %.1f%%, 기준 %.1f%%' % (
                max_row['mem_percent'],
                max_mem_usage_percent,
            ),
        )


CHECK_CLASS = Check
