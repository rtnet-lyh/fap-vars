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

WEBTOB-ROCKY-REPLAY-006

# is_required

필수

# inspection_name

프로세스 사용 상태 점검

# inspection_content

점유 리소스 사용률 점검

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

- 리소스 사용률: 시스템 자원을 특정 프로세스가 얼마나 사용하고 있는지를 나타내는 비율이며, CPU 사용률(%CPU)과 메모리 사용률(%MEM)이 리소스 사용률로 언급됨. 위 예시에서는 프로세스가 CPU의 12.3%, 시스템 메모리의 2%를 사용하고 있음

- **양호**: WebtoB 프로세스 상태(S)에 Z/T/D 상태가 포함되지 않은 상태
- **경고**: WebtoB 프로세스 상태(S)에 Z/T/D 상태가 포함된 상태
- **확인 필요**: 대상 프로세스가 없거나 top 출력에서 대상 프로세스를 찾지 못하는 상태

# thresholds

[
    {id: null, key: "process_name", value: "exTMS", sortOrder: 0}
,
{id: null, key: "bad_process_states", value: "Z,D,T", sortOrder: 1}
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
    DEFAULT_BAD_PROCESS_STATES = 'Z,D,T'
    COMMAND_TIMEOUT = 10

    def _parse_bad_states(self, raw_value):
        return {
            token.strip().upper()
            for token in re.split(r'[,| ]+', str(raw_value or ''))
            if token.strip()
        }

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
        process_name = self.get_host_var(key='process_name')
        if not process_name:
            process_name = self.get_threshold_var(
                'process_name', 
                default=self.DEFAULT_PROCESS_NAME, 
                value_type='str'
            ).strip()

        bad_states_raw = self.get_threshold_var(
            'bad_process_states',
            default=self.DEFAULT_BAD_PROCESS_STATES,
            value_type='str',
        )
        bad_states = self._parse_bad_states(bad_states_raw)
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
                message='WEB 프로세스 상태를 확인하지 못했습니다.',
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

        bad_rows = [
            row for row in rows
            if (row['state'] or '').strip().upper()[:1] in bad_states
        ]
        metrics = {
            'process_name': process_name,
            'process_count': len(rows),
            'states': sorted({row['state'] for row in rows}),
            'bad_process_count': len(bad_rows),
            'bad_processes': bad_rows,
            'processes': rows,
        }
        thresholds = {
            'process_name': process_name,
            'bad_process_states': sorted(bad_states),
        }

        if bad_rows:
            return self.warn(
                metrics=metrics,
                thresholds=thresholds,
                reasons='비정상 프로세스 상태가 발견되었습니다.',
                message='WEB 프로세스 상태 경고: 비정상 상태 %s건, 기준 %s' % (
                    len(bad_rows),
                    ','.join(sorted(bad_states)),
                ),
            )

        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='대상 프로세스 상태에 Z/D/T 상태가 없습니다.',
            message='WEB 프로세스 상태 정상: %s개 프로세스 상태=%s' % (
                len(rows),
                ','.join(metrics['states']),
            ),
        )


CHECK_CLASS = Check
