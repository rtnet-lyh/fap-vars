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


WEB-WTB-RKY-008

# is_required

필수

# inspection_name

서비스 제공 불가 점검

# inspection_content

사용자(클라이언트) 요청에 통신오류 서비스 불가와 비슷하게 WEB 서버가 응답하지 못해 발생(503:Service Temporary Unavailable), 서버 HW 자원사용률 과부하 또는 접속자 폭주 등으로 발생

# inspection_command

```bash
- error_log_path: /home/exTMS/tmax/webtob/log/main
```bash
grep "503" $(ls {{ error_log_path }}/error.log*|sort|tail -n 1)
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

- 503 상태 코드는 웹 서버가 일시적으로 서비스를 제공할 수 없는 상태를 의미하며, 서버 자원 부족이나 과부하로 인해 발생함. 이 오류가 발생할 경우, 서버 자원과 설정을 점검하여 문제를 해결하는 것이 필요하며, 빈번한 경우 성능 개선 조치 권고.

- **양호**: 상태코드 503이 포함된 로그가 없는 상태
- **경고**: 상태코드 503이 포함된 로그가 있는 상태
- **확인 필요**: 출력이 없거나 실행불가(권한/미설치 등)로 점검 불가한 상태

# thresholds

[
    {id: null, key: "error_log_path", value: "/home/exTMS/tmax/webtob/log/main", sortOrder: 0}
,
{id: null, key: "warning_status_code", value: "503", sortOrder: 1}
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
    DEFAULT_WARNING_STATUS_CODE = 503
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
            ).strip()

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
                message='WebtoB error log에서 503 상태를 확인하지 못했습니다.',
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
                reasons='error log에서 HTTP 503 관련 로그가 발견되었습니다.',
                message='WebtoB 503 상태 경고: count=%s' % len(matches),
            )

        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='error log에서 HTTP 503 관련 로그가 발견되지 않았습니다.',
            message='WebtoB 503 상태 정상: status=%s 미검출' % status_code,
        )


CHECK_CLASS = Check
