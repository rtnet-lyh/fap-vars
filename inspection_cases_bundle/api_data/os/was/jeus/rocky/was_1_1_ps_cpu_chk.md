# type_name

일상점검

# area_name

was

# category_name

상태점검

# application_type

jeus

# application

rocky

# inspection_code


WAS-JEUS-RKY-001

# is_required

필수

# inspection_name

프로세스 CPU 사용률

# inspection_content

WAS 서비스 부하 확인을 위한 WAS 프로세스가 사용하고 있는 CPU 자원 사용률 확인

# inspection_command

```bash

```

# inspection_output

```text
[root@tips_was1 jeus]# top -b -n 1 | egrep "PID|exTMS"
    PID USER      PR  NI    VIRT    RES    SHR S  %CPU  %MEM     TIME+ COMMAND
 419081 exTMS     20   0   11.5g   2.6g  34080 S   6.2  11.1 402:35.78 java
   1715 exTMSagn  20   0   89852   9564   8176 S   0.0   0.0   0:39.25 systemd
   1744 exTMSagn  20   0  153960   4064      4 S   0.0   0.0   0:00.00 (sd-pam)
   1931 exTMSagn  20   0 5088156 290296  17504 S   0.0   1.2  65:25.02 java
   2366 exTMSagn  20   0   64484   4932   4612 S   0.0   0.0   0:00.00 dbus-da+
 738307 exTMS     20   0   15.6g   8.9g  33672 S   0.0  38.1 397:00.07 java
1150460 exTMS     20   0   89872   9944   8320 S   0.0   0.0   0:29.51 systemd
1150464 exTMS     20   0  301424   4456      4 S   0.0   0.0   0:00.00 (sd-pam)
1150575 exTMS     20   0   64484   5424   4920 S   0.0   0.0   0:00.00 dbus-da+
1151048 exTMS     20   0  243708   5316   2884 S   0.0   0.0   0:03.28 tmux: s+
1151049 exTMS     20   0  226456   3484   3480 S   0.0   0.0   0:00.02 bash
1158057 exTMS     20   0 8012564 845004  27620 S   0.0   3.5 127:58.28 java
1158123 exTMS     20   0  222604   3092   3092 S   0.0   0.0   0:00.00 startNo+
1158124 exTMS     20   0 4969008 167684  19060 S   0.0   0.7  83:03.42 java
```

# description

- %CPU : 프로세스가 사용하는 CPU 사용률을 나타냄

- **양호**: CPU 사용률이 `max_cpu_usage_percent` 이하인 상태
- **경고**: CPU 사용률이 `max_cpu_usage_percent`를 초과하여 CPU 부하가 높은 상태
- **확인 필요**: 대상 프로세스가 없거나 top 출력에서 대상 프로세스를 찾지 못하는 상태

# thresholds

[
    {id: null, key: "max_cpu_usage_percent", value: "70", sortOrder: 0}
]

# inspection_script

# -*- coding: utf-8 -*-

from .common._base import BaseCheck


COMMAND = 'top -b -n 1 | egrep "PID|{process_name}"'
DEFAULT_PROCESS_NAME = 'exTMS'

class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'linux'
    PARAMIKO_REUSE_SESSION = False

    COMMAND_TIMEOUT = 20

    def _run_jeus_command(self):
        process_name = self.get_threshold_var(
            key='process_name',
            default=DEFAULT_PROCESS_NAME,
            value_type='str',
        )

        command = COMMAND.format(process_name=process_name)

        result = self._run_paramiko_commands(
            [{'command': command, 'timeout': self.COMMAND_TIMEOUT}],
            become=True,
            profile='linux',
        )[0]
        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()
        if result.get('rc') != 0:
            return stdout, stderr, self.fail(
                '점검 명령 실행 실패',
                message='JEUS 점검 명령 실행에 실패했습니다.',
                stdout=stdout,
                stderr=stderr,
            )
        return stdout, stderr, None

    def _parse_top_rows(self, stdout):
        rows = []
        header = []
        for line in stdout.splitlines():
            parts = line.split()
            if 'PID' in parts and '%CPU' in parts and '%MEM' in parts:
                header = parts
                continue
            if not header or len(parts) < len(header):
                continue
            try:
                rows.append({
                    'pid': parts[header.index('PID')],
                    'user': parts[header.index('USER')],
                    'state': parts[header.index('S')],
                    'cpu_percent': float(parts[header.index('%CPU')]),
                    'mem_percent': float(parts[header.index('%MEM')]),
                    'command': parts[header.index('COMMAND')],
                })
            except (ValueError, IndexError):
                continue
        return rows

    def run(self):
        stdout, _stderr, error = self._run_jeus_command()
        if error:
            return error
        rows = self._parse_top_rows(stdout)
        if not rows:
            return self.fail('프로세스 정보 없음', message='top 출력에서 대상 프로세스를 찾지 못했습니다.', stdout=stdout)
        threshold = self.get_threshold_var('max_cpu_usage_percent', default=80.0, value_type='float')
        max_row = max(rows, key=lambda row: row['cpu_percent'])
        over_rows = [row for row in rows if row['cpu_percent'] > threshold]
        metrics = {'process_name': 'exTMS', 'process_count': len(rows), 'max_cpu_usage_percent': max_row['cpu_percent'], 'max_cpu_pid': max_row['pid'], 'max_cpu_command': max_row['command'], 'over_threshold_count': len(over_rows), 'processes': rows}
        thresholds = {'max_cpu_usage_percent': threshold}
        if over_rows:
            return self.warn(metrics=metrics, thresholds=thresholds, reasons='CPU 사용률 기준 초과 프로세스가 있습니다.', message='JEUS 프로세스 CPU 사용률 경고: 최대 %.1f%%, 기준 %.1f%%' % (max_row['cpu_percent'], threshold))
        return self.ok(metrics=metrics, thresholds=thresholds, reasons='대상 프로세스 CPU 사용률이 기준 이하입니다.', message='JEUS 프로세스 CPU 사용률 정상: 최대 %.1f%%, 기준 %.1f%%' % (max_row['cpu_percent'], threshold))


CHECK_CLASS = Check
