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

WEBTOB-ROCKY-REPLAY-012

# is_required

필수

# inspection_name

접근 로그 점검

# inspection_content

사용자(클라이언트) 요청이 웹서버에 정상적으로 접속되어 서비스 되는지 WEB Access log 확인

# inspection_command

```bash
- access_log_path: /home/exTMS/tmax/webtob/log/main
```bash
awk '$(NF-2)=200' $(ls {{ access_log_path }}/access.log*|sort|tail -n 1) | tail -20
```
```

# inspection_output

```text
[root@tips_web1 main]# awk '$(NF-2)=200' $(ls /home/exTMS/tmax/webtob/log/main/access.log*|sort|tail -n 1) | tail -20
172.18.12.53 [08/May/2026:17:57:42 +0900] "POST /getNotiPopupInfo.do HTTP/1.1" 200 12 5
172.29.53.51 [08/May/2026:17:57:42 +0900] "GET /trafficMonitor/trafficData?source=trafficVdsCorrectionLine&sourceLayer=VDS_TRAFFIC_CORRECTION&_=1778222531851 HTTP/1.1" 200 10553961 156
172.18.12.53 [08/May/2026:17:57:42 +0900] "POST /getOpinionPopupInfo.do HTTP/1.1" 200 12 2
172.18.12.53 [08/May/2026:17:57:42 +0900] "POST /checkSession.do HTTP/1.1" 200 14 0
```

# description

- 접근 로그 점검: grep "200" 명령어를 사용하여 HTTP 상태 코드 200을 포함한 로그를 검색함. HTTP 상태 코드 200이 많이 발견되면 서비스가 정상적으로 운영되고 있으며, 상태 코드 200이 발견되지 않을 경우 서비스의 정상 작동 여부를 점검하고 문제를 해결을 권고.

- **양호**: HTTP 상태 코드 200이 발견되는 상태
- **경고**: HTTP 상태 코드 200이 발견되지 않는 상태
- **확인 필요**: 출력이 없거나 실행불가(권한/미설치 등)로 점검 불가한 상태

# thresholds

[
    {id: null, key: "access_log_path", value: "/home/exTMS/tmax/webtob/log/main", sortOrder: 0}
,
{id: null, key: "required_status_code", value: "200", sortOrder: 1}
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
    DEFAULT_REQUIRED_STATUS_CODE = 200
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
        required_status_code = self.get_host_var(key='required_status_code')

        access_log_path = self.get_threshold_var(
            'access_log_path', 
            default=self.DEFAULT_ACCESS_LOG_PATH, 
            value_type='str'
        ).strip()
        
        status_code = self.get_threshold_var(
            'required_status_code',
            default=self.DEFAULT_REQUIRED_STATUS_CODE,
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
                message='WebtoB access log에서 정상 응답 상태를 확인하지 못했습니다.',
                stdout=stdout,
                stderr=stderr,
            )

        matches = self._parse_status_lines(stdout, status_code)
        metrics = {
            'access_log_path': access_log_path,
            'required_status_code': status_code,
            'matching_status_count': len(matches),
            'sample_lines': matches[:20],
        }
        thresholds = {
            'access_log_path': access_log_path,
            'required_status_code': status_code,
        }

        if not matches:
            return self.warn(
                metrics=metrics,
                thresholds=thresholds,
                reasons='최신 access log에서 HTTP 200 응답을 찾지 못했습니다.',
                message='WebtoB access log 정상 응답 확인 경고: status=%s 미검출' % status_code,
            )

        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='최신 access log에서 HTTP 200 응답을 확인했습니다.',
            message='WebtoB access log 정상 응답 확인 정상: status=%s, count=%s' % (
                status_code,
                len(matches),
            ),
        )


CHECK_CLASS = Check
