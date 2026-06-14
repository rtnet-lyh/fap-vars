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

WEBTOB-ROCKY-REPLAY-016

# is_required

필수

# inspection_name

WEB 서비스 불가 점검

# inspection_content

WEB엔진, 어플리케이션 소스 오류 등으로 인한 WEB 서비스 자체 불가 확인 (500:Internal Server Error),사용자 폭주, 서버 상태 이상 시 발생

# inspection_command

```bash
- error_log_path: /home/exTMS/tmax/webtob/log/main
```bash
grep "500" $(ls {{ error_log_path }}/error.log*|sort|tail -n 1)
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

- 500 상태 코드가 포함된 로그 항목은 서버 내부 오류를 의미하며, 오류가 발생한 경우, 서버나 애플리케이션 로그를 조사하여 근본적인 원인을 파악하고 수정 필요.

- **양호**: 상태코드 500이 포함된 로그가 없는 상태
- **경고**: 상태코드 500이 포함된 로그가 있는 상태
- **확인 필요**: 출력이 없거나 실행불가(권한/미설치 등)로 점검 불가한 상태

# thresholds

[
    {id: null, key: "error_log_path", value: "/home/exTMS/tmax/webtob/log/main", sortOrder: 0}
,
{id: null, key: "warning_status_code", value: "500", sortOrder: 1}
]

# inspection_script

# -*- coding: utf-8 -*-

from .common._base import BaseCheck


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'linux'
    PARAMIKO_REUSE_SESSION = False

    DEFAULT_ERROR_LOG_PATH = '/home/exTMS/tmax/webtob/log/main'
    DEFAULT_WARNING_STATUS_CODE = 500
    COMMAND_TIMEOUT = 10

    def _build_command(self, error_log_path, status_code):
        path = error_log_path.rstrip('/')
        return 'grep "%s" $(ls %s/error.log*|sort|tail -n 1)' % (status_code, path)

    def run(self):
        error_log_path = self.get_host_var(key='error_log_path')

        if not error_log_path:
            error_log_path = self.get_threshold_var(
                'error_log_path', 
                default=self.DEFAULT_ERROR_LOG_PATH, 
                value_type='str'
            ).strip() or self.DEFAULT_ERROR_LOG_PATH

        status_code = self.get_threshold_var(
            'warning_status_code',
            default=self.DEFAULT_WARNING_STATUS_CODE,
            value_type='int',
        )
        command = self._build_command(error_log_path, status_code)

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
                message='WebtoB error log에서 500 상태를 확인하지 못했습니다.',
                stdout=stdout,
                stderr=stderr,
            )

        matches = [line.strip() for line in stdout.splitlines() if str(status_code) in line]
        metrics = {
            'error_log_path': error_log_path,
            'warning_status_code': status_code,
            'matching_status_count': len(matches),
            'sample_lines': matches[:20],
        }
        thresholds = {
            'error_log_path': error_log_path,
            'warning_status_code': status_code,
        }

        if matches:
            return self.warn(
                metrics=metrics,
                thresholds=thresholds,
                reasons='error log에서 HTTP 500 관련 로그가 발견되었습니다.',
                message='WebtoB 500 상태 경고: count=%s' % len(matches),
            )

        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='error log에서 HTTP 500 관련 로그가 발견되지 않았습니다.',
            message='WebtoB 500 상태 정상: status=%s 미검출' % status_code,
        )


CHECK_CLASS = Check
