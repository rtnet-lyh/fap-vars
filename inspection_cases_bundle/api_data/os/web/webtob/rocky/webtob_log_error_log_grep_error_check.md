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

WEBTOB-ROCKY-REPLAY-015

# is_required

필수

# inspection_name

에러 로그 점검

# inspection_content

웹서버 엔진 자체적으로 서비스 요청, 응답, 내부처리 등에 문제가 발생 시 출력하는 로그로 특이사항 점검

# inspection_command

```bash
- error_log_path: /home/exTMS/tmax/webtob/log/main
```bash
grep "error" $(ls {{ error_log_path }}/error.log*|sort|tail -n 1)
```
```

# inspection_output

```text
(예방점검 예시와 다름, 명령어 확인 필요)
```text
[2026-05-12T13:32:07] [CLIENT(127.0.0.1)] [E] [ERR-00045] A request does not belong to any virtual host or node. Access is denied. {server address=127.0.0.1:9080, host:127.0.0.1} HEAD / HTTP/1.1
```
```

# description

- 에러 로그를 통해 웹 서버의 문제를 식별하며, 특히 ERROR 레벨의 로그와 구체적인 에러 메시지를 통해 문제의 심각성을 판단함. 최근 로그를 검토하고, CRITICAL 및 FATAL 에러는 즉시 대응이 필요.

- **양호**: CRITICAL 및 FATAL 에러가 없는 상태
- **경고**: CRITICAL 및 FATAL 에러가 있는 상태
- **확인 필요**: 출력이 없거나 실행불가(권한/미설치 등)로 점검 불가한 상태

# thresholds

[
    {id: null, key: "error_log_path", value: "/home/exTMS/tmax/webtob/log/main", sortOrder: 0}
,
{id: null, key: "critical_patterns", value: "CRITICAL|FATAL", sortOrder: 1}
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

    DEFAULT_ERROR_LOG_PATH = '/home/exTMS/tmax/webtob/log/main'
    DEFAULT_CRITICAL_PATTERNS = 'CRITICAL|FATAL'
    COMMAND_TIMEOUT = 10

    def _build_command(self, error_log_path):
        path = error_log_path.rstrip('/')
        return 'grep -Ei "CRITICAL|FATAL|ERR-|error" $(ls %s/error.log*|sort|tail -n 1) | tail -20' % path

    def run(self):
        error_log_path = self.get_host_var(key='error_log_path')

        if not error_log_path:
            error_log_path = self.get_threshold_var(
                'error_log_path', 
                default=self.DEFAULT_ERROR_LOG_PATH, 
                value_type='str'
            ).strip() or self.DEFAULT_ERROR_LOG_PATH

        critical_patterns = self.get_threshold_var(
                'critical_patterns',
                default=self.DEFAULT_CRITICAL_PATTERNS,
                value_type='str',
        ).strip()
        
        command = self._build_command(error_log_path)

        result = self._run_paramiko_commands(
            [{'command': command, 'timeout': self.COMMAND_TIMEOUT}],
            become=True,
            profile='linux',
        )[0]

        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()
        if result.get('rc') != 0:
            return self.fail(
                'error log 명령 실행 실패',
                message='WebtoB error log를 확인하지 못했습니다.',
                stdout=stdout,
                stderr=stderr,
            )

        lines = [line.strip() for line in stdout.splitlines() if line.strip()]
        pattern = re.compile(critical_patterns, re.IGNORECASE)
        critical_lines = [line for line in lines if pattern.search(line)]
        metrics = {
            'error_log_path': error_log_path,
            'inspected_line_count': len(lines),
            'critical_fatal_count': len(critical_lines),
            'critical_fatal_lines': critical_lines[:20],
            'sample_lines': lines[:20],
        }
        thresholds = {
            'error_log_path': error_log_path,
            'critical_patterns': critical_patterns,
        }

        if critical_lines:
            return self.warn(
                metrics=metrics,
                thresholds=thresholds,
                reasons='error log에서 CRITICAL 또는 FATAL 로그가 발견되었습니다.',
                message='WebtoB error log 경고: critical_fatal_count=%s' % len(critical_lines),
            )

        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='error log에서 CRITICAL/FATAL 로그가 발견되지 않았습니다.',
            message='WebtoB error log 정상: inspected_line_count=%s, critical_fatal_count=0' % len(lines),
        )


CHECK_CLASS = Check
