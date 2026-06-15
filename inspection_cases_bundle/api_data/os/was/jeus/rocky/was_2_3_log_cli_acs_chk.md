# type_name

일상점검

# area_name

was

# category_name

상태점검

# application_type

jeus

# application

rocky

# inspection_code


WAS-JEUS-RKY-007

# is_required

필수

# inspection_name

클라이언트 접속 기록 로그 이상 유무 점검

# inspection_content

각 서비스 컨테이너별 액세스 로그 점검(HTTP Code 400, 500번대 로그 발생 여부 확인)

# inspection_command

```bash

```

# inspection_output

```text

```

# description

- HTTP Status Code: 400대 클라이언트 오류나 500대 서버 오류가 발생한 빈도와 원인을 분석하여, 각각 클라이언트 측 문제 또는 서버 설정을 점검 필요.

- **양호**: 출력값에 400대 클라이언트 오류 혹은 500대 서버 오류가 발생하지 않은 경우
- **경고**: 출력값에 400대 클라이언트 오류 혹은 500대 서버 오류가 발생한 경우
- **확인 필요**: 출력이 없거나 실행불가(권한/미설치 등)로 점검 불가한 상태

# thresholds

[]

# inspection_script

# -*- coding: utf-8 -*-

from .common._base import BaseCheck
import re

COMMAND = "tail -50 $(ls -t {admin_log_path}/*.log | head -1)"


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'linux'
    PARAMIKO_REUSE_SESSION = False

    COMMAND_TIMEOUT = 20

    def _run_jeus_command(self, admin_log_path):

        command = COMMAND.format(admin_log_path=admin_log_path)

        result = self._run_paramiko_commands(
            [{'command': command, 'timeout': self.COMMAND_TIMEOUT}],
            become=True,
            profile='linux',
        )[0]

        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()
        if result.get('rc') != 0:
            return stdout, stderr, self.fail(
                '점검 명령 실행 실패',
                message='JEUS 점검 명령 실행에 실패했습니다.',
                stdout=stdout,
                stderr=stderr,
            )

        return stdout, stderr, None

    FINDING_LABEL = 'HTTP 400/500대 오류'

    def _parse_access_log(self, output: str, bad_status_bands: list[int]):
        results = []

        for line in output.splitlines():
            line = line.strip()
            if not line:
                continue
            
            match = re.search(r'"[^"]+"\s+(\d{3})\s+', line)
            if not match:
                continue

            status_code = int(match.group(1))
            status_band = status_code // 100

            is_bad = status_band in bad_status_bands

            results.append({
                "status_code": status_code,
                "status_band": f"{status_band}xx",
                "is_bad": is_bad,
                "line": line,
            })

        return results

    def run(self):
        admin_log_path = self.get_threshold_var(
            key='admin_log_path',
            default='/home/exTMS/tmax/jeus/log/adminServer/servlet',
            value_type='str',
        )

        bad_status_bands = self.get_threshold_var(
            key='bad_status_bands', 
            default='4,5', 
            value_type='str'
        )

        bad_status_bands = re.split(r'[,|]+', bad_status_bands)
        bad_status_bands = [int(band) for band in bad_status_bands]                

        stdout, _stderr, error = self._run_jeus_command(admin_log_path)

        ok_items = []
        fail_items = []
        metrics = {}
        thresholds = {}

        if error:
            return error
        
        results = self._parse_access_log(stdout, bad_status_bands)

        if results:
            metrics = {
                "results": results
            }

            ok_items = [item for item in results if not item["is_bad"]]
            bad_items = [item for item in results if item["is_bad"]]

        is_pass = True if not bad_items else False

        thresholds = {
            'bad_status_bands': bad_status_bands, 
            'admin_log_path': admin_log_path
        }

        if is_pass:
            return self.ok(
                metrics=metrics, 
                thresholds=thresholds, 
                reasons=f"HTTP Staud Code에 {bad_status_bands}가 존재하지 않습니다.", 
                message=f"HTTP Staud Code에 {bad_status_bands}가 존재하지 않습니다.", 
            )
        else:    
            return self.warn(
                metrics=metrics, 
                thresholds=thresholds, 
                reasons=f"HTTP Staud Code에 {bad_status_bands}가 존재합니다.", 
                message=f"HTTP Staud Code에 {bad_status_bands}가 존재합니다.", 
            )


CHECK_CLASS = Check
