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

WEBTOB-ROCKY-REPLAY-008

# is_required

필수

# inspection_name

서비스 포트 오픈 상태 점검

# inspection_content

WEB 프로세스 기동 시 생성되는 사용자 접속 Port가 정상적으로 오픈되었는지 확인을 통해 URL 서비스 포트로 접속 가능한 상태인지 점검

# inspection_command

```bash
- webtob_service_port 변수
```bash
netstat -an | grep "{{ webtob_service_port }}" # webtob_service_port: 9080
```
```

# inspection_output

```text
[root@sd_tipswebwas log]# netstat -an | grep 9080
tcp        0      0 0.0.0.0:9080            0.0.0.0:*               LISTEN
```

# description

- 프로토콜: tcp 또는 tcp6이어야 하며, 다른 경우에는 포트 설정 검토를 권고. 
- 로컬 주소 및 포트: 서비스에 설정된 포트와 일치하고 LISTEN 상태여야 하며, 포트가 다를 경우 포트 설정 점검. 
- 상태: LISTEN 상태여야 하며, 그렇지 않을 경우 서비스 시작이나 문제 해결 필요.

- **양호**: 프로토콜이 tcp 또는 tcp6이면서 `allow_stats`가 LISTEN 상태
- **경고**: 프로토콜이 tcp 또는 tcp6이 아니거나 `allow_stats`가 LISTEN이 아닌 상태
- **확인 필요**: 출력이 비어 있거나 명령 실행 불가/권한/미지원 등의 사유로 점검 불가한 상태

# thresholds

[
    {id: null, key: "webtob_service_port", value: "9080", sortOrder: 0}
,
{id: null, key: "allow_state", value: "LISTEN", sortOrder: 1}
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

    DEFAULT_SERVICE_PORT = 9080
    DEFAULT_ALLOW_STATE = 'LISTEN'
    COMMAND_TIMEOUT = 10

    def _parse_netstat_rows(self, stdout):
        rows = []
        for line in str(stdout or '').splitlines():
            parts = re.split(r'\s+', line.strip())
            if len(parts) < 6 or parts[0] not in ('tcp', 'tcp6'):
                continue
            rows.append({
                'protocol': parts[0],
                'recv_q': parts[1],
                'send_q': parts[2],
                'local_address': parts[3],
                'foreign_address': parts[4],
                'state': parts[5],
            })
        return rows

    def run(self):
        service_port = self.get_host_var(key='webtob_service_port')

        if not service_port:
            service_port = self.get_threshold_var(
                'webtob_service_port',
                default=self.DEFAULT_SERVICE_PORT,
                value_type='int',
            )
            
        allow_state = str(
            self.get_threshold_var('allow_state', default=self.DEFAULT_ALLOW_STATE, value_type='str') or ''
        ).strip().upper() or self.DEFAULT_ALLOW_STATE
        command = 'netstat -an | grep %s' % service_port

        result = self._run_paramiko_commands(
            [{'command': command, 'timeout': self.COMMAND_TIMEOUT}],
            become=True,
            profile='linux',
        )[0]

        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()
        if result.get('rc') != 0:
            return self.fail(
                'netstat 명령 실행 실패',
                message='WebtoB 서비스 포트 상태를 확인하지 못했습니다.',
                stdout=stdout,
                stderr=stderr,
            )

        rows = self._parse_netstat_rows(stdout)
        if not rows:
            return self.fail(
                '서비스 포트 정보 없음',
                message='netstat 출력에서 대상 포트를 찾지 못했습니다.',
                stdout=stdout,
                stderr=stderr,
            )

        listening_rows = [
            row for row in rows
            if row['protocol'] in ('tcp', 'tcp6') and row['state'].upper() == allow_state
        ]
        metrics = {
            'webtob_service_port': service_port,
            'connection_count': len(rows),
            'listen_count': len(listening_rows),
            'connections': rows,
        }
        thresholds = {
            'webtob_service_port': service_port,
            'allow_state': allow_state,
            'allow_protocols': ['tcp', 'tcp6'],
        }

        if not listening_rows:
            return self.warn(
                metrics=metrics,
                thresholds=thresholds,
                reasons='대상 포트가 LISTEN 상태가 아닙니다.',
                message='WebtoB 서비스 포트 오픈 경고: port=%s, listen_count=0' % service_port,
            )

        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='대상 포트가 tcp LISTEN 상태입니다.',
            message='WebtoB 서비스 포트 오픈 정상: port=%s, listen_count=%s' % (
                service_port,
                len(listening_rows),
            ),
        )


CHECK_CLASS = Check
