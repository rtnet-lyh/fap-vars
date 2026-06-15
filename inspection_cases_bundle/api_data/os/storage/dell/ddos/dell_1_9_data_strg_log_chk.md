# type_name

일상점검

# area_name

storage

# category_name

상태점검

# application_type

dell

# application

ddos

# inspection_code


ST-DELL-DDOS-013

# is_required

필수

# inspection_name

데이터 스토리지 디스크

# inspection_content

스토리지 디스크 Fault 여부

# inspection_command

```bash
disk status
```

# inspection_output

```text

```

# description

- disk status 명령어를 통해 스토리지 디스크 운영 상태 및 장애 여부를 확인할 수 있음
- Storage operational 상태를 통해 스토리지 정상 동작 여부를 점검 가능하며, 디스크 장애 (Fail) 및 스토리지 비정상 상태 여부를 확인할 수 있음

- **양호**: 출력 결과가 `valid_disk_status`와 일치할 경우
- **경고**: 출력 결과가 `valid_disk_status`와 일치하지 않을 경우
- **확인 필요**: 명령어 수행 실패 또는 출력 결과를 확인할 수 없는 경우

# thresholds

[
    {id: null, key: "valid_disk_status", value: "Normal - Storage operational", sortOrder: 0}
]

# inspection_script

# -*- coding: utf-8 -*-

from .common._base import BaseCheck


COMMAND_ERROR_MARKERS = ('syntax error', 'unknown command', 'invalid command', 'command not found')
COMMAND = 'disk status'
BAD_DISK_WORDS = ('failed', 'failure', 'error', 'offline', 'degraded')
DEFAULT_VALID_DISK_STATUS = 'Normal - Storage operational'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'generic_network'
    PARAMIKO_REUSE_SESSION = True

    def _detect_cli_error(self, *texts):
        for text in texts:
            for line in str(text or '').splitlines():
                stripped = line.strip()
                lowered = stripped.lower()
                if stripped and any(marker in lowered for marker in COMMAND_ERROR_MARKERS):
                    return stripped
        return ''

    def _run_command(self):
        results = self._run_paramiko_commands([COMMAND], profile=self.PARAMIKO_PROFILE)
        if not results:
            return None, self.fail('점검 명령 실행 실패', message='Paramiko 명령 실행 결과가 비어 있습니다.')
        result = results[0]
        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()
        if result.get('rc') != 0:
            return None, self.fail('점검 명령 실행 실패', message=f'{COMMAND} 명령 실행에 실패했습니다.', stdout=stdout, stderr=stderr)
        error_text = self._detect_cli_error(stdout, stderr)
        if error_text:
            return None, self.fail('점검 명령 실행 실패', message=f'{COMMAND} 명령 출력에서 오류가 확인되었습니다: {error_text}', stdout=stdout, stderr=stderr)
        return stdout, None

    def run(self):
        valid_status = str(self.get_threshold_var('valid_disk_status', default=DEFAULT_VALID_DISK_STATUS, value_type='str')).strip()
        thresholds = {'valid_disk_status': valid_status, 'bad_disk_words': list(BAD_DISK_WORDS)}
        stdout, error = self._run_command()
        if error:
            return error

        bad_lines = [line.strip() for line in stdout.splitlines() if any(word in line.lower() for word in BAD_DISK_WORDS)]
        has_valid_status = valid_status.lower() in stdout.lower()
        metrics = {'has_valid_disk_status': has_valid_status, 'bad_disk_lines': bad_lines}
        if not has_valid_status or bad_lines:
            return self.fail('Disk 상태 기준 미달', message='Storage 정상 문구가 없거나 디스크 장애 키워드가 확인되었습니다.', stdout=stdout, metrics=metrics, thresholds=thresholds)
        return self.ok(metrics=metrics, thresholds=thresholds, reasons='Storage 정상 문구가 있고 디스크 장애 키워드가 없습니다.', message='Disk 상태 점검 정상.')


CHECK_CLASS = Check
