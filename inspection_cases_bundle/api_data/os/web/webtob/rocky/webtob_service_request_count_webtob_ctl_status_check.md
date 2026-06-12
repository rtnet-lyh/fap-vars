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

WEBTOB-ROCKY-REPLAY-011

# is_required

권고

# inspection_name

사용자 요청량 처리 수 점검

# inspection_content

WEB 서비스 지연 시 상태 확인을 위해 WEB 환경 설정값과 사용자 요청건수가 적절하게 설정되었는지 확인

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

- MaxConnections: 동시에 처리 가능한 최대 연결 수를 설정하며, 설정값이 서버의 처리 용량에 적합한지 확인하고 조정하는 것이 권고. 
- MaxRequestPerConnection: 하나의 연결에서 처리할 수 있는 최대 요청 수를 설정하며, 요청 패턴에 맞추어 적절한 값 설정 필요. 
- MaxWorkerThreads: 요청을 처리할 수 있는 최대 워커 스레드 수를 설정하며, 서버 성능에 맞는 적절한 수치 설정 권고.

- **양호**: `max_connections`, `max_request_per_connection`, `max_worker_threads`가 적절한 수치인 상태
- **경고**: `max_connections`, `max_request_per_connection`, `max_worker_threads`가 적절하지 않은 상태
- **확인 필요**: webtob_ctl 명령이 없거나 실행불가(권한/미설치 등)로 점검 불가한 상태

# thresholds

[
    {id: null, key: "min_max_connections", value: "1000", sortOrder: 0}
,
{id: null, key: "min_max_request_per_connection", value: "50", sortOrder: 1}
,
{id: null, key: "min_max_worker_threads", value: "200", sortOrder: 2}
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
    DEFAULT_MIN_MAX_CONNECTIONS = 1000
    DEFAULT_MIN_MAX_REQUEST_PER_CONNECTION = 50
    DEFAULT_MIN_MAX_WORKER_THREADS = 200
    COMMAND_TIMEOUT = 10

    def _parse_status(self, stdout):
        values = {}
        for line in str(stdout or '').splitlines():
            match = re.match(r'^\s*([A-Za-z][A-Za-z0-9_]*)\s*:\s*(.*?)\s*$', line)
            if match:
                values[match.group(1)] = match.group(2)
        return values

    def _parse_int_value(self, values, key):
        raw_value = str(values.get(key) or '').strip()
        if not raw_value:
            return None
        match = re.search(r'\d+', raw_value)
        if not match:
            return None
        return int(match.group(0))

    def run(self):
        min_max_connections = self.get_threshold_var(
            'min_max_connections',
            default=self.DEFAULT_MIN_MAX_CONNECTIONS,
            value_type='int',
        )
        min_max_request_per_connection = self.get_threshold_var(
            'min_max_request_per_connection',
            default=self.DEFAULT_MIN_MAX_REQUEST_PER_CONNECTION,
            value_type='int',
        )
        min_max_worker_threads = self.get_threshold_var(
            'min_max_worker_threads',
            default=self.DEFAULT_MIN_MAX_WORKER_THREADS,
            value_type='int',
        )

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
                message='WebtoB 요청 처리 설정값을 확인하지 못했습니다.',
                stdout=stdout,
                stderr=stderr,
            )

        values = self._parse_status(stdout)
        actual_values = {
            'MaxConnections': self._parse_int_value(values, 'MaxConnections'),
            'MaxRequestPerConnection': self._parse_int_value(values, 'MaxRequestPerConnection'),
            'MaxWorkerThreads': self._parse_int_value(values, 'MaxWorkerThreads'),
        }
        missing = [key for key, value in actual_values.items() if value is None]
        if missing:
            return self.fail(
                '요청 처리 설정값 파싱 실패',
                message='webtob_ctl status 출력에서 설정값을 확인하지 못했습니다: %s' % ', '.join(missing),
                stdout=stdout,
                stderr=stderr,
            )

        thresholds = {
            'min_max_connections': min_max_connections,
            'min_max_request_per_connection': min_max_request_per_connection,
            'min_max_worker_threads': min_max_worker_threads,
        }
        checks = {
            'MaxConnections': actual_values['MaxConnections'] >= min_max_connections,
            'MaxRequestPerConnection': actual_values['MaxRequestPerConnection'] >= min_max_request_per_connection,
            'MaxWorkerThreads': actual_values['MaxWorkerThreads'] >= min_max_worker_threads,
        }
        failed = [key for key, passed in checks.items() if not passed]
        metrics = {
            'webtob_ctl_values': values,
            'request_count_values': actual_values,
            'passed_checks': checks,
            'failed_checks': failed,
        }

        if failed:
            return self.warn(
                metrics=metrics,
                thresholds=thresholds,
                reasons='일부 요청 처리 설정값이 기준보다 낮습니다.',
                message='WebtoB 요청 처리 설정 경고: 기준 미달=%s' % ', '.join(failed),
            )

        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='요청 처리 설정값이 모두 기준 이상입니다.',
            message='WebtoB 요청 처리 설정 정상: MaxConnections=%s, MaxRequestPerConnection=%s, MaxWorkerThreads=%s' % (
                actual_values['MaxConnections'],
                actual_values['MaxRequestPerConnection'],
                actual_values['MaxWorkerThreads'],
            ),
        )


CHECK_CLASS = Check
