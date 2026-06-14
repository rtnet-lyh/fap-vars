# type_name

일상점검

# area_name

network

# category_name

상태점검

# application_type

juniper_junos

# application

ex4300

# inspection_code

NETWORK-JUNIPER-JUNOS-EX4300-4-1-SYSLOG

# is_required

필수

# inspection_name

시스템 로그

# inspection_content

HW 상태와 관련된 ERROR 로그(Fail, Error, Warning, Stop, Down) 발생 여부 점검

# inspection_command

```bash
show log messages | match "fail|error|warning|stop|down"
```

# inspection_output

```text
falcon@Center_Server_J4300_B> show log
                                   ^
syntax error, expecting <command>.
```

# description

- 명령어: 장비에 기록된 시스템 로그를 확인하는 명령어.
- 권한문제로 인한 로그 확인 불가

- **양호**: 결과 값 미 출력
- **경고**: 결과 값 출력
- **확인 필요**: 명령어 실패

# thresholds

[]

# inspection_script

# -*- coding: utf-8 -*-

from .common._base import BaseCheck


COMMAND_ERROR_MARKERS = ('syntax error', 'unknown command', 'invalid command', 'unknown keyword', 'missing argument')
COMMAND = 'show log messages | match "fail|error|warning|stop|down"'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'generic_network'
    PARAMIKO_REUSE_SESSION = True

    def _run_command(self, command):
        results = self._run_paramiko_commands([command], profile=self.PARAMIKO_PROFILE)
        if not results:
            return None, self.fail('점검 명령 실행 실패', message='Paramiko 명령 실행 결과가 비어 있습니다.')
        result = results[0]
        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()
        if result.get('rc') != 0:
            return None, self.fail('점검 명령 실행 실패', message=f'{command} 명령 실행에 실패했습니다.', stdout=stdout, stderr=stderr)
        error_text = self._detect_cli_error(stdout, stderr)
        if error_text:
            return None, self.fail('점검 명령 실행 실패', message=f'{command} 명령 출력에서 오류가 확인되었습니다: {error_text}', stdout=stdout, stderr=stderr)
        return stdout, None

    def _detect_cli_error(self, *texts):
        for text in texts:
            for line in str(text or '').splitlines():
                stripped = line.strip()
                lowered = stripped.lower()
                if stripped and any(marker in lowered for marker in COMMAND_ERROR_MARKERS):
                    return stripped
        return ''

    def run(self):
        stdout, error = self._run_command(COMMAND)
        if error:
            return error

        matched_lines = [line.strip() for line in stdout.splitlines() if line.strip()]
        metrics = {'matched_log_line_count': len(matched_lines), 'matched_log_lines': matched_lines}
        if matched_lines:
            return self.fail('시스템 로그 기준 미달', message=f'HW 관련 오류 키워드 로그가 {len(matched_lines)}건 확인되었습니다.', stdout=stdout, metrics=metrics, thresholds={})
        return self.ok(metrics=metrics, thresholds={}, reasons='HW 관련 오류 키워드 로그가 출력되지 않았습니다.', message='시스템 로그 점검 정상.')


CHECK_CLASS = Check
