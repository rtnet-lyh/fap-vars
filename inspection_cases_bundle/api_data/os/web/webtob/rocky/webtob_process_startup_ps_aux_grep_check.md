# type_name

일상점검

# area_name

web

# category_name

상태점검

# application_type

webtob

# application

rocky

# inspection_code

WEBTOB-ROCKY-REPLAY-007

# is_required

필수

# inspection_name

프로세스 기동 점검

# inspection_content

WEB 서비스를 위한 WEB 프로세스가 정상적으로 기동 되었는지를 점검

# inspection_command

```bash
- process_name 변수
```bash
 ps aux | egrep "PID|webtob" | grep -v grep
```
```

# inspection_output

```text
[root@sd_tipswebwas ~]# ps aux | grep webtob | grep -v grep
exTMS    1476176  0.0  5.8 6052980 940596 ?      Sl    2025  93:32 /usr/lib/jvm/jdk-1.8.0_431-oracle-x64/bin/java -DadminServer -Xms1024m -Xmx1024m -XX:MetaspaceSize=128m -XX:MaxMetaspaceSize=512m -d64 -Djeus.vm.bits=64 -Djeus.io.buffer.size-per-pool=81920 -Djeus.cdi.enabled=false -Djeus.jms.server.manager.produce-wait-strategy-type=blocking -Djeus.servlet.sortWebinfLibraries=name_asc -server -Xbootclasspath/p:/home/exTMS/tmax/jeus/lib/system/extension.jar -classpath /home/exTMS/tmax/jeus/lib/jbext/jbext_v8500_202502_2_unified.jar:/home/exTMS/tmax/jeus/lib/system/bootstrap.jar -Djava.security.policy=/home/exTMS/tmax/jeus/domains/jeus_domain/config/security/policy -Djava.library.path=/home/exTMS/tmax/jeus/lib/system:/home/exTMS/tmax/webtob/lib: -Djava.endorsed.dirs=/home/exTMS/tmax/jeus/lib/endorsed -Djeus.properties.replicate=jeus,sun.rmi,java.util,java.net -Djeus.jvm.version=hotspot -Djava.util.logging.config.file=/home/exTMS/tmax/jeus/bin/logging.properties -Dsun.rmi.dgc.server.gcInterval=3600000 -Djava.util.logging.manager=jeus.util.logging.JeusLogManager -Djeus.home=/home/exTMS/tmax/jeus -Djeus.launcher.log.home=/home/exTMS/tmax/jeus/log/launcher -Djava.net.preferIPv4Stack=true -Djeus.tm.checkReg=true -Dsun.rmi.dgc.client.gcInterval=3600000 -Djeus.domain.name=jeus_domain -Djava.naming.factory.initial=jeus.jndi.JNSContextFactory -Djava.naming.factory.url.pkgs=jeus.jndi.jns.url -Djeus.server.protectmode=false -XX:+UnlockDiagnosticVMOptions -XX:+LogVMOutput -XX:LogFile=/home/exTMS/tmax/jeus/log/adminServer/jvm.log jeus.server.admin.DomainAdminServerBootstrapper -domain jeus_domain -u wasadmin -server adminServer
exTMS    1480138  0.0  0.0  19032  8728 ?        S     2025   8:27 wsm -l 0x2 -I webtob1_1480137 -b 1480137
exTMS    1480139  0.0  0.0  12588   900 ?        S     2025   2:40 htl -l 0x2 -I webtob1_1480137 -b 1480137
exTMS    1480140  0.0  3.6 1211928 596944 ?      Sl    2025   3:13 hth -l 0x2 -I webtob1_1480137 -b 1480137
```

# description

- PID: 프로세스의 고유 식별 번호를 나타내며, 정상적으로 기동된 경우 유효한 PID가 있어야 
하며, 비정상적인 PID 발견 시 점검이 필요. 해당 프로세스가 실행 중이지 않으면 PID가 
표시되지 않음. 
- COMMAND: 실행 중인 명령어와 경로를 나타내며, 명령어가 정확하게 실행되고 있는지 확인해야 함. ※ 프로세스 상태 ‘S’는 프로세스가 CPU를 사용하지 않고 대기 상태(Sleeping)임을 의미하고, ‘s’는 세션 리더 프로세스(자식 프로세스를 생성하고, 해당 세션의 제어를 담당하는 프로세스)임을 나타내므로, ‘Ss’는 해당 프로세스가 CPU 자원을 대기 중이면서 세션을 관리하고 있음을 의미함.

- **양호**: 유효한 PID가 있고 비정상적인 상태 코드(Z, D, T)가 발견되지 않은 상태
- **경고**: 비정상적인 상태 코드(Z, D, T)가 발견된 상태
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

    def _parse_ps_rows(self, stdout):
        rows = []
        for line in str(stdout or '').splitlines():
            parts = re.split(r'\s+', line.strip(), maxsplit=10)
            if len(parts) < 11 or not parts[1].isdigit():
                continue
            try:
                rows.append({
                    'user': parts[0],
                    'pid': parts[1],
                    'cpu_percent': float(parts[2]),
                    'mem_percent': float(parts[3]),
                    'stat': parts[7],
                    'start': parts[8],
                    'time': parts[9],
                    'command': parts[10],
                })
            except (ValueError, IndexError):
                continue
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
        command = 'ps aux | grep %s | grep -v grep' % process_name

        result = self._run_paramiko_commands(
            [{'command': command, 'timeout': self.COMMAND_TIMEOUT}],
            become=True,
            profile='linux',
        )[0]

        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()
        if result.get('rc') != 0:
            return self.fail(
                'ps 명령 실행 실패',
                message='WEB 프로세스 기동 상태를 확인하지 못했습니다.',
                stdout=stdout,
                stderr=stderr,
            )

        rows = self._parse_ps_rows(stdout)
        if not rows:
            return self.fail(
                '프로세스 정보 없음',
                message='ps 출력에서 대상 프로세스를 찾지 못했습니다.',
                stdout=stdout,
                stderr=stderr,
            )

        bad_rows = [
            row for row in rows
            if any(state in (row['stat'] or '').upper() for state in bad_states)
        ]

        metrics = {
            'process_name': process_name,
            'process_count': len(rows),
            'pids': [row['pid'] for row in rows],
            'states': sorted({row['stat'] for row in rows}),
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
                reasons='기동 중인 WEB 프로세스에서 비정상 상태가 발견되었습니다.',
                message='WEB 프로세스 기동 경고: 비정상 상태 %s건, 기준 %s' % (
                    len(bad_rows),
                    ','.join(sorted(bad_states)),
                ),
            )

        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='유효한 PID가 있고 비정상 상태 코드가 없습니다.',
            message='WEB 프로세스 기동 정상: %s개 프로세스 PID=%s' % (
                len(rows),
                ','.join(metrics['pids']),
            ),
        )


CHECK_CLASS = Check
