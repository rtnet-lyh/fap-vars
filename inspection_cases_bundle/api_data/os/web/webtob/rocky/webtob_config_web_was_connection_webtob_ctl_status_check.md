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


WEB-WTB-RKY-001

# is_required

권고

# inspection_name

WEB-WAS 연동상태 점검

# inspection_content

WEB-WAS 커넥션 상태가 지속적으로 연결되어 있어야 웹서버로 요청 시 WAS 응답 후 정상적인 서비스가 이뤄졌는지 점검(만료 시 Https 서비스 시 보안 취약 발생)

# inspection_command

```bash
webtob_ctl status
```

# inspection_output

```text
Status: RUNNING
MaxConnections: 1000
MaxRequestPerConnection: 50
MaxWorkerThreads: 200
```

# description

- Status: RUNNING 상태는 WebtoB와 WAS 간의 커넥션이 정상적으로 유지되고 있음을 나타냄. 상태가 RUNNING이 아닌 STOPPED나 ERROR 상태 라면, 시스템 로그 확인 점검 필요

- **양호**: `connection_status`가 RUNNING인 상태
- **경고**: `connection_status`가 RUNNING이 아닌 STOPPED나 ERROR인 상태
- **확인 필요**: webtob_ctl 명령이 없거나 실행불가(권한/미설치 등)로 점검 불가한 상태

# thresholds

[
    {id: null, key: "connection_status", value: "RUNNING", sortOrder: 0}
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

    COMMAND = 'webtob_ctl status'
    DEFAULT_CONNECTION_STATUS = 'RUNNING'
    COMMAND_TIMEOUT = 10

    def _parse_status(self, stdout):
        values = {}
        for line in str(stdout or '').splitlines():
            match = re.match(r'^\s*([A-Za-z][A-Za-z0-9_]*)\s*:\s*(.*?)\s*$', line)
            if match:
                values[match.group(1)] = match.group(2)
        return values

    def run(self):
        expected_status = str(
            self.get_threshold_var(
                'connection_status',
                default=self.DEFAULT_CONNECTION_STATUS,
                value_type='str',
            ) or ''
        ).strip().upper() or self.DEFAULT_CONNECTION_STATUS

        result = self._run_paramiko_commands(
            [{'command': self.COMMAND, 'timeout': self.COMMAND_TIMEOUT}],
            become=True,
            profile='linux',
        )[0]

        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()
        if result.get('rc') != 0:
            return self.fail(
                'webtob_ctl 명령 실행 실패',
                message='WEB-WAS 연동 상태를 확인하지 못했습니다.',
                stdout=stdout,
                stderr=stderr,
            )

        values = self._parse_status(stdout)
        actual_status = str(values.get('Status') or '').strip().upper()
        if not actual_status:
            return self.fail(
                'WEB-WAS 상태 파싱 실패',
                message='webtob_ctl status 출력에서 Status 값을 확인하지 못했습니다.',
                stdout=stdout,
                stderr=stderr,
            )

        metrics = {
            'connection_status': actual_status,
            'webtob_ctl_values': values,
        }
        thresholds = {
            'connection_status': expected_status,
        }

        if actual_status != expected_status:
            return self.warn(
                metrics=metrics,
                thresholds=thresholds,
                reasons='WEB-WAS 연동 상태가 RUNNING이 아닙니다.',
                message='WEB-WAS 연동 상태 경고: status=%s, expected=%s' % (
                    actual_status,
                    expected_status,
                ),
            )

        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='WEB-WAS 연동 상태가 RUNNING입니다.',
            message='WEB-WAS 연동 상태 정상: status=%s' % actual_status,
        )


CHECK_CLASS = Check
