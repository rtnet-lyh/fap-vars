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

WEBTOB-ROCKY-REPLAY-013

# is_required

필수

# inspection_name

요청 문서 처리 불가 점검

# inspection_content

사용자(클라이언트)가 요청한 문서 또는 웹페이지를 찾을 수 없는 상태(404:Not Found), 소스 위치 변경 또는 삭제된 문서(웹페이지 포함)에서 발생

# inspection_command

```bash
- access_log_path: /home/exTMS/tmax/webtob/log/main
```bash
awk '$(NF-2)=404' $(ls {{ access_log_path }}/access.log*|sort|tail -n 1) | tail -20
```
```

# inspection_output

```text
[root@tips_web1 main]# awk '$(NF-2)=404' $(ls /home/exTMS/tmax/webtob/log/main/access.log*|sort|tail -n 1) | tail -20
172.29.41.55 [08/May/2026:17:53:55 +0900] "POST /getOpinionPopupInfo.do HTTP/1.1" 404 12 6
172.25.37.142 [08/May/2026:17:53:55 +0900] "POST /getLtrsInfoList.do HTTP/1.1" 404 991 18
172.34.41.60 [08/May/2026:17:53:55 +0900] "POST /getVmsAutoTargetDrfInfo.do HTTP/1.1" 404 5418 21
172.29.41.55 [08/May/2026:17:53:55 +0900] "POST /checkSession.do HTTP/1.1" 404 14 4
```

# description

- 자주 발생하는 404 오류는 웹 페이지나 문서의 실제 위치를 검토하고, 링크가 올바르게 설정되었는지 확인하거나 삭제된 페이지에 대해 적절한 대체 페이지를 제공하는 것이 필요

- **양호**: 응답시간이 `max_response_time`을 초과하지 않는 상태
- **경고**: 응답시간이 `max_response_time`을 초과한 상태
- **확인 필요**: 출력이 없거나 실행불가(권한/미설치 등)로 점검 불가한 상태

# thresholds

[
    {id: null, key: "access_log_path", value: "/home/exTMS/tmax/webtob/log/main", sortOrder: 0}
,
{id: null, key: "warning_status_code", value: "404", sortOrder: 1}
]

# inspection_script

# -*- coding: utf-8 -*-

from .common._base import BaseCheck


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'linux'
    PARAMIKO_REUSE_SESSION = False

    DEFAULT_ACCESS_LOG_PATH = '/home/exTMS/tmax/webtob/log/main'
    DEFAULT_WARNING_STATUS_CODE = 404
    COMMAND_TIMEOUT = 10

    def _build_command(self, access_log_path, status_code):
        path = access_log_path.rstrip('/')
        return "awk '$(NF-2)==%s' $(ls %s/access.log*|sort|tail -n 1) | tail -20" % (
            status_code,
            path,
        )

    def _parse_status_lines(self, stdout, status_code):
        matches = []
        for line in str(stdout or '').splitlines():
            parts = line.split()
            if len(parts) < 3:
                continue
            if parts[-3] == str(status_code):
                matches.append(line.strip())
        return matches

    def run(self):
        access_log_path = self.get_host_var(key='access_log_path')

        if not access_log_path:
            access_log_path = self.get_threshold_var(
                'access_log_path', 
                default=self.DEFAULT_ACCESS_LOG_PATH, 
                value_type='str'
            ).strip()

        status_code = self.get_threshold_var(
            'warning_status_code',
            default=self.DEFAULT_WARNING_STATUS_CODE,
            value_type='int',
        )

        command = self._build_command(access_log_path, status_code)

        result = self._run_paramiko_commands(
            [{'command': command, 'timeout': self.COMMAND_TIMEOUT}],
            become=True,
            profile='linux',
        )[0]

        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()
        
        if result.get('rc') != 0:
            return self.fail(
                'access log 명령 실행 실패',
                message='WebtoB access log에서 404 응답을 확인하지 못했습니다.',
                stdout=stdout,
                stderr=stderr,
            )

        matches = self._parse_status_lines(stdout, status_code)
        metrics = {
            'access_log_path': access_log_path,
            'warning_status_code': status_code,
            'matching_status_count': len(matches),
            'sample_lines': matches[:20],
        }
        thresholds = {
            'access_log_path': access_log_path,
            'warning_status_code': status_code,
        }

        if matches:
            return self.warn(
                metrics=metrics,
                thresholds=thresholds,
                reasons='최신 access log에서 HTTP 404 응답이 발견되었습니다.',
                message='WebtoB access log 404 응답 경고: count=%s' % len(matches),
            )

        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='최신 access log에서 HTTP 404 응답이 발견되지 않았습니다.',
            message='WebtoB access log 404 응답 정상: status=%s 미검출' % status_code,
        )


CHECK_CLASS = Check
