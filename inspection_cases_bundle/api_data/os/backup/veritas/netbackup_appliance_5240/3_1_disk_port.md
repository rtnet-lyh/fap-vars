# type_name

일상점검

# area_name

backup

# category_name

상태점검

# application_type

veritas

# application

netbackup_appliance_5240

# inspection_code


BK-NBU5240-009

# is_required

필수

# inspection_name

용량 점검

# inspection_content

백업 수행 용량(기존 백업 용량과 차이 확인) 및 포트 사용 상태 점검

# inspection_command

```bash
/usr/openv/pdde/pdcr/bin/crcontrol --dsstat && netstat -tuln | grep LISTEN
```

# inspection_output

```text
netbackup:/home/maintenance # /usr/openv/pdde/pdcr/bin/crcontrol --dsstat && netstat -tuln | grep LISTEN

************ Data Store statistics ************
Data storage      Raw     Size    Used    Avail   Use%    Free%
                  34.8T   33.4T   13.9T   19.5T   42%     58.3%

Number of containers             : 207392
Average container size           : 73505465 bytes (70.10MB)
Space allocated for containers   : 15244445468144 bytes (13.86TB)
Reserved space                   : 1540390020096 bytes (1.40TB)
Reserved space percentage        : 4.0%
Reserved space for cloud cache   : 0.0B (0.0%)

Use "--dsstat 1" to get more accurate statistics
Use "--dsstat 2" to get statistics for each partition
Use "--dsstat 3" to get more accurate statistics for each partition

tcp        0      0 0.0.0.0:13778           0.0.0.0:*               LISTEN
tcp        0      0 0.0.0.0:13779           0.0.0.0:*               LISTEN
tcp        0      0 127.0.0.1:3443          0.0.0.0:*               LISTEN
tcp        0      0 127.0.0.1:2323          0.0.0.0:*               LISTEN
tcp        0      0 127.0.0.1:13780         0.0.0.0:*               LISTEN
tcp        0      0 0.0.0.0:1556            0.0.0.0:*               LISTEN
tcp        0      0 127.0.0.1:36629         0.0.0.0:*               LISTEN
tcp        0      0 127.0.0.1:36821         0.0.0.0:*               LISTEN
tcp        0      0 127.0.0.1:1557          0.0.0.0:*               LISTEN
tcp        0      0 0.0.0.0:42581           0.0.0.0:*               LISTEN
```

# description

- /usr/openv/pdde/pdcr/bin/crcontrol --dsstat 명령어: MSDP 저장소의 용량 사용 현황을 확인하는 명령어.
- netstat -tuln | grep LISTEN 명령어: 현재 장비에서 LISTEN 중인 TCP/UDP 포트를 확인하는 명령어.

- **양호**: 'Use%'가 `max_usage_percent` 이하이고, 주소 값 중 : 다음 값이 `denied_ports`와 일치하지 않는 경우.
- **경고**: 'Use%'가 `max_usage_percent` 초과이거나, 주소 값 중 : 다음 값이 `denied_ports`와 일치할 경우.
- **확인 필요**: 명령어 실패 및 파싱 불가.

# thresholds

[
    {id: null, key: "max_usage_percent", value: "80", sortOrder: 0}
,
{id: null, key: "denied_ports", value: "", sortOrder: 1}
]

# inspection_script

# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


COMMAND = '/usr/openv/pdde/pdcr/bin/crcontrol --dsstat && netstat -tuln | grep LISTEN'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'    
    PARAMIKO_REUSE_SESSION = True
    PARAMIKO_COMMAND_TIMEOUT = 5 
    PARAMIKO_AUTH_TIMEOUT_SEC = 20  

    def _denied_ports(self):
        raw = self.get_threshold_var('denied_ports', default='', value_type='str')
        return [item.strip() for item in str(raw or '').split(',') if item.strip()]

    def _run_command(self):
        try:
            self.get_elevate_for_aos()
        except Exception as exc:
            return None, self.fail('AOS 권한 상승 실패', message=str(exc))

        result = self._run_paramiko_commands(
            [{'command': COMMAND, 'timeout': 10}],
            
        )[0]
        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()
        if self._is_connection_error(result.get('rc'), stderr):
            return None, self.fail('호스트 연결 실패', message=stderr or 'Paramiko 연결 확인에 실패했습니다.', stderr=stderr)
        if result.get('rc') != 0:
            return None, self.fail('점검 명령 실행 실패', message='용량 및 LISTEN 포트 조회 명령 실행에 실패했습니다.', stdout=stdout, stderr=stderr)
        return stdout, None

    def _parse_usage_percent(self, stdout):
        for line in str(stdout or '').splitlines():
            match = re.match(r'^\s*\S+\s+\S+\s+\S+\s+\S+\s+([0-9.]+)%\s+([0-9.]+)%', line)
            if match:
                return float(match.group(2))
        return None

    def _parse_listen_ports(self, stdout):
        ports = []
        for line in str(stdout or '').splitlines():
            parts = line.split()
            if len(parts) < 4 or 'LISTEN' not in parts:
                continue
            local_address = parts[3]
            port = local_address.rsplit(':', 1)[-1]
            if port.isdigit():
                ports.append(port)
        return ports

    def run(self):
        stdout, error = self._run_command()
        if error:
            return error

        max_usage_percent = self.get_threshold_var('max_usage_percent', default=80, value_type='float')
        denied_ports = self._denied_ports()
        thresholds = {
            'max_usage_percent': max_usage_percent,
            'denied_ports': ','.join(denied_ports),
        }

        usage_percent = self._parse_usage_percent(stdout)
        listen_ports = self._parse_listen_ports(stdout)
        
        if usage_percent is None or not listen_ports:
            return self.fail('용량 또는 포트 출력 파싱 실패', message='Use% 또는 LISTEN 포트 값을 해석하지 못했습니다.', stdout=stdout, thresholds=thresholds)

        denied_found = sorted(set(port for port in listen_ports if port in denied_ports))
        metrics = {
            'usage_percent': usage_percent,
            'listen_port_count': len(listen_ports),
            'listen_ports': listen_ports,
            'denied_ports_found': denied_found,
        }
        if usage_percent > max_usage_percent or denied_found:
            return self.fail(error='Use%가 기준을 초과했거나 금지 포트가 LISTEN 상태입니다.', metrics=metrics, thresholds=thresholds, reasons='Use%가 기준을 초과했거나 금지 포트가 LISTEN 상태입니다.', message='용량/포트 상태 경고: Use%%=%s, 금지 포트=%s.' % (usage_percent, ','.join(denied_found) or '없음'))
        return self.ok(metrics=metrics, thresholds=thresholds, reasons='Use%가 기준 이하이고 금지 포트가 LISTEN 상태가 아닙니다.', message='용량 및 LISTEN 포트 점검 정상')


CHECK_CLASS = Check
