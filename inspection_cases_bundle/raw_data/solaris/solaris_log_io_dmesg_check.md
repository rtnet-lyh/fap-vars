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

SVR-5-9

# is_required

필수

# inspection_name

I/O 에러 로그

# inspection_content

Solaris 커널 메시지에서 I/O 오류, 타임아웃, 전송 실패, 미디어 오류를 점검합니다.

# inspection_command

```bash
dmesg | grep -i 'timeout|i/o error|transport failed|media error'
```

# inspection_output

```text
I/O Error: Device /dev/sda1 reported error
Timeout occurred while waiting for device
Transport failed for SCSI device /dev/sdb
Media error detected on /dev/sdc
```

# description

- I/O 오류, 타임아웃, 전송 실패, 미디어 에러를 확인.
  - 스토리지 장치 상태와 연결 경로를 함께 점검해야 함.

# thresholds

[
    {id: null, key: "failure_keywords", value: "장치를 찾을 수 없습니다,not found,module,cannot,command not found", sortOrder: 0}
]

# inspection_script

# -*- coding: utf-8 -*-

from .common._base import BaseCheck


LOG_COMMAND = "dmesg | grep -i 'timeout|i/o error|transport failed|media error'"
LOG_PATTERNS = (
    'timeout',
    'i/o error',
    'transport failed',
    'media error',
)


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def _split_keywords(self, raw_value):
        return [token.strip() for token in str(raw_value or '').split(',') if token.strip()]

    def _build_log_summary(self, lines, limit=3):
        if not lines:
            return 'I/O 이상 로그 없음'

        summary_lines = [line.strip() for line in lines[:limit]]
        if len(lines) > limit:
            summary_lines.append(f'외 {len(lines) - limit}건')
        return ' | '.join(summary_lines)

    def _count_pattern_hits(self, lines):
        counts = {}
        lowered_lines = [line.lower() for line in lines]
        for pattern in LOG_PATTERNS:
            counts[pattern.replace(' ', '_').replace('/', '_')] = sum(
                1 for line in lowered_lines if pattern in line
            )
        return counts

    def run(self):
        failure_keywords = self._split_keywords(
            self.get_threshold_var(
                'failure_keywords',
                default='장치를 찾을 수 없습니다,not found,module,cannot,command not found',
                value_type='str',
            )
        )

        rc, out, err = self._ssh(LOG_COMMAND)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'SSH 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        text = (out or '').strip()
        stderr_text = (err or '').strip()
        combined_text = '\n'.join(value for value in (text, stderr_text) if value)

        command_error = self._detect_command_error(
            text,
            stderr_text,
            extra_patterns=failure_keywords + [
                'permission denied',
                'illegal option',
                'invalid option',
                'usage:',
            ],
        )
        if command_error:
            return self.fail(
                '점검 명령 실행 실패',
                message=(
                    'Solaris 입출력 작동 이상 유무 점검에 실패했습니다. '
                    f'현재 상태: 명령 출력에서 실행 오류가 확인되었습니다: {command_error}'
                ),
                stdout=text,
                stderr=stderr_text,
            )

        if rc not in (0, 1):
            return self.fail(
                '점검 명령 실행 실패',
                message=(
                    'Solaris 입출력 작동 이상 유무 점검에 실패했습니다. '
                    f'현재 상태: {LOG_COMMAND} 명령 종료코드가 rc={rc}로 반환되었습니다.'
                ),
                stdout=text,
                stderr=stderr_text,
            )

        if stderr_text:
            return self.fail(
                '점검 명령 실행 실패',
                message=(
                    'Solaris 입출력 작동 이상 유무 점검에 실패했습니다. '
                    f'현재 상태: stderr 출력이 확인되었습니다: {stderr_text}'
                ),
                stdout=text,
                stderr=stderr_text,
            )

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        matched_failure_keywords = [
            keyword for keyword in failure_keywords
            if keyword.lower() in combined_text.lower()
        ]
        pattern_hit_count = self._count_pattern_hits(lines)

        metrics = {
            'command_rc': rc,
            'matched_log_count': len(lines),
            'matched_logs': lines,
            'matched_failure_keywords': matched_failure_keywords,
            'stderr_line_count': len([line for line in stderr_text.splitlines() if line.strip()]),
            'timeout_count': pattern_hit_count['timeout'],
            'io_error_count': pattern_hit_count['i_o_error'],
            'transport_failed_count': pattern_hit_count['transport_failed'],
            'media_error_count': pattern_hit_count['media_error'],
        }

        if lines:
            return self.fail(
                'I/O 오류 로그 감지',
                message=(
                    'Solaris 입출력 작동 이상 유무 점검에 실패했습니다. '
                    f'현재 상태: I/O 오류 관련 로그 {len(lines)}건이 확인되었습니다. '
                    f'timeout {pattern_hit_count["timeout"]}건, '
                    f'i/o error {pattern_hit_count["i_o_error"]}건, '
                    f'transport failed {pattern_hit_count["transport_failed"]}건, '
                    f'media error {pattern_hit_count["media_error"]}건입니다. '
                    f'첫 로그: {lines[0]}. 로그 요약: {self._build_log_summary(lines)}.'
                ),
                metrics=metrics,
                thresholds={
                    'failure_keywords': failure_keywords,
                },
                stdout=text,
                stderr=stderr_text,
            )

        return self.ok(
            metrics=metrics,
            thresholds={
                'failure_keywords': failure_keywords,
            },
            reasons=(
                'I/O 오류, timeout, transport failed, media error 패턴 로그가 검출되지 않았고 '
                '실행 오류나 stderr도 없습니다.'
            ),
            message=(
                'Solaris 입출력 작동 이상 유무 점검이 정상입니다. '
                '현재 상태: timeout 0건, i/o error 0건, transport failed 0건, '
                'media error 0건, stderr 0건으로 집계되었습니다.'
            ),
        )


CHECK_CLASS = Check
