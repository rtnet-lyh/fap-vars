# type_name

일상점검(상태점검)

# area_name

서버

# category_name

LOG

# application_type

UNIX

# application

solaris

# inspection_code

SVR-5-3

# is_required

필수

# inspection_name

CPU 로그

# inspection_content

Solaris 커널 메시지에서 CPU 하드웨어 오류와 오프라인 상태 로그가 있는지 점검합니다.

# inspection_command

```bash
dmesg | grep -i 'ecc error|uncorrectable|offline'
```

# inspection_output

```text
ECC error detected on CPU0
Uncorrectable ECC error on CPU1
CPU2 offline due to hardware failure
```

# description

- ECC 오류, 정정 불가 오류, CPU 오프라인 상태를 확인.
  - 해당 메시지가 있으면 CPU 모듈 점검 또는 교체 필요.

# thresholds

[
    {id: null, key: "failure_keywords", value: "장치를 찾을 수 없습니다,not found,cannot,command not found,module missing", sortOrder: 0}
]

# inspection_script

# -*- coding: utf-8 -*-

from .common._base import BaseCheck


LOG_COMMAND = "dmesg | grep -i 'ecc error|uncorrectable|offline'"


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def _build_log_summary(self, lines, limit=3):
        if not lines:
            return 'CPU 이상 로그 없음'

        summary_lines = [line.strip() for line in lines[:limit]]
        if len(lines) > limit:
            summary_lines.append(f'외 {len(lines) - limit}건')
        return ' | '.join(summary_lines)

    def run(self):
        failure_keywords_raw = self.get_threshold_var('failure_keywords', default='', value_type='str')

        rc, out, err = self._ssh(LOG_COMMAND)
        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'SSH 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )
        if rc not in (0, 1):
            return self.fail(
                '점검 명령 실행 실패',
                message=(
                    'Solaris CPU 로그 점검에 실패했습니다. '
                    "현재 상태: dmesg | grep -i 'ecc error|uncorrectable|offline' 명령을 정상적으로 실행하지 못했습니다."
                ),
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        text = (out or '').strip()
        stderr_text = (err or '').strip()
        failure_keywords = [keyword.strip() for keyword in failure_keywords_raw.split(',') if keyword.strip()]
        combined_text = '\n'.join([value for value in (text, stderr_text) if value])
        matched_failure_keywords = [keyword for keyword in failure_keywords if keyword.lower() in combined_text.lower()]
        if matched_failure_keywords:
            return self.fail(
                'CPU 로그 실패 키워드 감지',
                message=(
                    'Solaris CPU 로그 점검에 실패했습니다. '
                    f'현재 상태: 출력에서 실패 키워드 {matched_failure_keywords}가 확인되었습니다.'
                ),
                stdout=text,
                stderr=stderr_text,
            )
        if stderr_text:
            return self.fail(
                '점검 명령 실행 실패',
                message=(
                    'Solaris CPU 로그 점검에 실패했습니다. '
                    f'현재 상태: stderr 출력이 확인되었습니다: {stderr_text}'
                ),
                stdout=text,
                stderr=stderr_text,
            )

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if lines:
            return self.fail(
                'CPU 오류 로그 감지',
                message=(
                    'Solaris CPU 로그 점검에 실패했습니다. '
                    f'현재 상태: ECC error, uncorrectable, offline 관련 로그 {len(lines)}건이 확인되었습니다. '
                    f'첫 로그: {lines[0]}. 로그 요약: {self._build_log_summary(lines)}.'
                ),
                stdout=text,
                stderr=stderr_text,
            )

        return self.ok(
            metrics={
                'matched_log_count': len(lines),
                'matched_logs': lines,
                'matched_failure_keywords': matched_failure_keywords,
            },
            thresholds={
                'failure_keywords': failure_keywords,
            },
            reasons='CPU 하드웨어 오류 관련 로그가 검출되지 않았고 stderr도 없습니다.',
            message='Solaris CPU 로그가 정상입니다. 현재 상태: ECC error, uncorrectable, offline 관련 로그 0건, stderr 0건으로 집계되었습니다.',
        )


CHECK_CLASS = Check
