# type_name

일상점검

# area_name

network

# category_name

상태점검

# application_type

piolink_pas

# application

pas_k3200x

# inspection_code


NW-PIO-K3200X-012

# is_required

필수

# inspection_name

시스템 로그

# inspection_content

HW 상태와 관련된 Error 로그(Fail, Error, Warning, Stop, Down) 발생 유무 점검

# inspection_command

```bash
show log
```

# inspection_output

```text

```

# description

※ 로그레벨
- (notice): 일반 운영 정보
- (warning): 경고
- (err): 오류
- (fail): 기능 실패
- (down): 인터페이스/서비스 비정상 상태

- **양호**: (err), (fail), (down), (stop), (warning) 관련 치명 로그 미발생 상태
- **경고**: (err), (fail), (down), (stop), (warning) 관련 치명 로그 발생 상태
- **확인 필요**: 명령어 수행 실패 또는 출력 결과를 확인할 수 없는 경우

# thresholds

[]

# inspection_script

# -*- coding: utf-8 -*-

import re
from datetime import datetime

from .common._base import BaseCheck


COMMAND = 'show log keyword {today}'
BAD_LOG_RE = re.compile(r'\((?:err|fail|down|stop|warning)\)', re.IGNORECASE)


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'generic_network'
    PARAMIKO_REUSE_SESSION = True

    def _run_command(self):
        today = datetime.now().strftime("%Y/%m/%d")
        results = self._run_paramiko_commands([COMMAND.format(today=today)], profile=self.PARAMIKO_PROFILE)
        if not results:
            return None, self.fail('점검 명령 실행 실패', message='Paramiko 명령 실행 결과가 비어 있습니다.')
        result = results[0]
        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()
        if result.get('rc') not in [0, 124]:
            return None, self.fail('점검 명령 실행 실패', message=f'{COMMAND} 명령 실행에 실패했습니다.', stdout=stdout, stderr=stderr)
        return stdout, None

    def run(self):
        stdout, error = self._run_command()
        if error:
            return error

        log_lines = [line.strip() for line in (stdout or '').splitlines() if line.strip()]
        bad_logs = [line for line in log_lines if BAD_LOG_RE.search(line)]
        metrics = {
            'log_line_count': len(log_lines),
            'bad_log_count': len(bad_logs),
            'bad_logs': bad_logs,
        }
        if bad_logs:
            return self.fail(error="치명 또는 경고 로그 패턴이 확인되었습니다.", metrics=metrics, thresholds={}, reasons='치명 또는 경고 로그 패턴이 확인되었습니다.', message=f'시스템 로그 경고: 대상 로그 {len(bad_logs)}건.')
        return self.ok(metrics=metrics, thresholds={}, reasons='(err), (fail), (down), (stop), (warning) 로그가 확인되지 않았습니다.', message=f'시스템 로그 점검 정상: 로그 {len(log_lines)}건 확인.')


CHECK_CLASS = Check
