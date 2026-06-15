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


WEB-WTB-RKY-015

# is_required

필수

# inspection_name

서비스 포트 접속 정상 확인

# inspection_content

출발지Ip에서 목적지Ip 포트로 통신이 정상적으로 이뤄지는지 점검(방화벽 또는 보안장비 차단 여부 확인)

# inspection_command

```bash
- ip_addr 변수, webtob_service_port 변수
```bash
telnet {{ ip_addr }} {{ webtob_service_port }}
```
```

# inspection_output

```text
[root@sd_tipswebwas ~]# telnet 172.18.9.3 9080
Trying 172.18.9.3...
Connected to 172.18.9.3.
Escape character is '^]'.
```

# description

- 연결 상태: 연결 성공 여부를 나타내며, 연결이 성공하면 메시지가 표시됨.(Connected to)
[목적지 IP] 메시지가 출력되어야 함. 연결 실패 시 방화벽 또는 보안 장비의 설정 점검 필요.

- **양호**: "Connected to" 문구가 있는 경우
- **경고**: "Connected refused", "time out", "No route to host", "Unable to connect" 등의 문구가 있는 경우
- **확인 필요**: telnet 명령이 없거나 실행불가(권한/미설치 등)로 점검 불가한 상태

# thresholds

[
    {id: null, key: "ip_addr", value: "127.0.0.1", sortOrder: 0}
,
{id: null, key: "webtob_service_port", value: "9080", sortOrder: 1}
]

# inspection_script

# -*- coding: utf-8 -*-

from .common._base import BaseCheck


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'linux'
    PARAMIKO_REUSE_SESSION = False

    DEFAULT_IP_ADDR = '127.0.0.1'
    DEFAULT_SERVICE_PORT = 9080
    COMMAND_TIMEOUT = 10

    def run(self):
        ip_addr = self.get_host_var(key='ip_addr')
        webtob_service_port = self.get_host_var(key='webtob_service_port')

        if not ip_addr:
            ip_addr = self.get_threshold_var(
                'ip_addr', 
                default=self.DEFAULT_IP_ADDR, 
                value_type='str'
            ).strip()

        if not webtob_service_port:
            service_port = self.get_threshold_var(
                'webtob_service_port',
                default=self.DEFAULT_SERVICE_PORT,
                value_type='int',
            )

        command = 'echo quit | telnet %s %s' % (ip_addr, service_port)

        result = self._run_paramiko_commands(
            [{'command': command, 'timeout': self.COMMAND_TIMEOUT}],
            become=True,
            profile='linux',
        )[0]

        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()
        if result.get('rc') != 0:
            return self.fail(
                'telnet 명령 실행 실패',
                message='WebtoB 서비스 포트 접속을 확인하지 못했습니다.',
                stdout=stdout,
                stderr=stderr,
            )

        connected = 'Connected to' in stdout
        metrics = {
            'ip_addr': ip_addr,
            'webtob_service_port': service_port,
            'connected': connected,
        }
        thresholds = {
            'ip_addr': ip_addr,
            'webtob_service_port': service_port,
            'success_marker': 'Connected to',
        }

        if not connected:
            return self.warn(
                metrics=metrics,
                thresholds=thresholds,
                reasons='telnet 출력에서 Connected to 문구를 찾지 못했습니다.',
                message='WebtoB 서비스 포트 접속 경고: %s:%s 연결 확인 실패' % (
                    ip_addr,
                    service_port,
                ),
            )

        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='telnet 접속 출력에서 Connected to 문구를 확인했습니다.',
            message='WebtoB 서비스 포트 접속 정상: %s:%s' % (
                ip_addr,
                service_port,
            ),
        )


CHECK_CLASS = Check
