# -*- coding: utf-8 -*-

import re
import shlex

from .common._base import BaseCheck


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'linux'
    PARAMIKO_REUSE_SESSION = False

    DEFAULT_COMMAND_TIMEOUT = 10
    FAP_RC_MARKER = '__FAP_RC__'
    LOG_NOT_FOUND_MARKER = '__FAP_LOG_NOT_FOUND__'
    LATEST_LOG_MARKER = '__FAP_LATEST_LOG__'

    def _split_csv(self, raw_value, default_tokens=None):
        tokens = [
            token.strip()
            for token in str(raw_value or '').split(',')
            if token.strip()
        ]
        if tokens:
            return tokens
        return list(default_tokens or [])

    def _line_count(self, text):
        return len([line for line in str(text or '').splitlines() if line.strip()])

    def _quote(self, value):
        return shlex.quote(str(value or ''))

    def _get_failure_keywords(self):
        return self._split_csv(
            self.get_threshold_var(
                'failure_keywords',
                default=(
                    'command not found,not found,No such file,'
                    'No such file or directory,Permission denied,cannot,'
                    'Connection refused,No route to host,timed out,'
                    'PARAMIKO_CONNECTION_ERROR,PARAMIKO_COMMAND_TIMEOUT'
                ),
                value_type='str',
            )
        )

    def _contains_failure_keyword(self, *texts):
        failure_keywords = self._get_failure_keywords()
        combined = '\n'.join(str(text or '') for text in texts if text is not None)
        lowered = combined.lower()

        for keyword in failure_keywords:
            keyword_text = str(keyword or '').strip()
            if keyword_text and keyword_text.lower() in lowered:
                return keyword_text
        return ''

    def _extract_marker_rc(self, text):
        marker_pattern = re.escape(self.FAP_RC_MARKER) + r'(\d+)'
        matches = list(re.finditer(marker_pattern, str(text or '')))
        if not matches:
            return None
        try:
            return int(matches[-1].group(1))
        except Exception:
            return None

    def _extract_latest_log_file(self, text):
        for line in str(text or '').splitlines():
            stripped = line.strip()
            if stripped.startswith(self.LATEST_LOG_MARKER):
                return stripped[len(self.LATEST_LOG_MARKER):].strip()
        return ''

    def _remove_control_lines(self, text):
        rc_pattern = re.escape(self.FAP_RC_MARKER) + r'\d+'
        cleaned = []
        for line in str(text or '').splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped == self.LOG_NOT_FOUND_MARKER:
                continue
            if stripped.startswith(self.LATEST_LOG_MARKER):
                continue
            if re.search(rc_pattern, stripped):
                continue
            cleaned.append(line)
        return '\n'.join(cleaned).strip()


    def _stdout_without_matched_lines(self, cleaned_stdout, matched_lines):
        matched_set = set(str(line or '').strip() for line in (matched_lines or []))
        remaining = []
        for line in str(cleaned_stdout or '').splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped in matched_set:
                continue
            remaining.append(line)
        return '\n'.join(remaining).strip()

    def _run_command(self, command, timeout=None):
        timeout = self.DEFAULT_COMMAND_TIMEOUT if timeout is None else timeout
        results = self._run_paramiko_commands(
            [
                {
                    'command': command,
                    'timeout': timeout,
                }
            ],
            profile=self.PARAMIKO_PROFILE,
        )
        if not results:
            return {
                'command': command,
                'rc': 1,
                'stdout': '',
                'stderr': '명령 실행 결과가 비어 있습니다.',
                'timed_out': False,
            }
        return results[0]

    def _load_thresholds(self):
        error_log_path = self.get_threshold_var(
            'error_log_path',
            default='/home/exTMS/tmax/webtob/log/main',
            value_type='str',
        )

        error_keywords_raw = self.get_threshold_var(
            'error_keywords',
            default='CRITICAL,FATAL',
            value_type='str',
        )
        error_keywords = self._split_csv(
            error_keywords_raw,
            default_tokens=['CRITICAL', 'FATAL'],
        )
        if not error_keywords:
            error_keywords = ['CRITICAL', 'FATAL']

        sample_line_limit = self.get_threshold_var(
            'sample_line_limit',
            default=20,
            value_type='int',
        )
        try:
            sample_line_limit = int(sample_line_limit)
        except Exception:
            sample_line_limit = 20
        if sample_line_limit < 1:
            sample_line_limit = 1

        return {
            'error_log_path': str(error_log_path or '').strip() or '/home/exTMS/tmax/webtob/log/main',
            'error_keywords': error_keywords,
            'sample_line_limit': sample_line_limit,
            'failure_keywords': self._get_failure_keywords(),
        }

    def _build_error_regex(self, keywords):
        escaped = [re.escape(str(keyword).strip()) for keyword in keywords if str(keyword).strip()]
        if not escaped:
            escaped = [re.escape('CRITICAL'), re.escape('FATAL')]
        return '|'.join(escaped)

    def _base_metrics(self, result, stdout, stderr, thresholds, command, marker_rc=None, matched_lines=None, latest_log_file=''):
        matched_lines = list(matched_lines or [])
        sample_line_limit = thresholds.get('sample_line_limit')
        sampled_lines = matched_lines[:sample_line_limit]
        return {
            'command': command,
            'command_rc': result.get('rc'),
            'timed_out': bool(result.get('timed_out', False)),
            'stdout_line_count': self._line_count(stdout),
            'stderr_line_count': self._line_count(stderr),
            'error_log_path': thresholds.get('error_log_path'),
            'latest_log_file': latest_log_file or '',
            'error_keywords': thresholds.get('error_keywords'),
            'sample_line_limit': sample_line_limit,
            'marker_rc': marker_rc,
            'matched_count': len(matched_lines),
            'sampled_lines': sampled_lines,
            'first_matched_line': sampled_lines[0] if sampled_lines else '',
            'has_critical_or_fatal': bool(matched_lines),
        }

    def _thresholds_for_result(self, thresholds):
        return {
            'error_log_path': thresholds.get('error_log_path'),
            'error_keywords': thresholds.get('error_keywords'),
            'sample_line_limit': thresholds.get('sample_line_limit'),
            'failure_keywords': thresholds.get('failure_keywords'),
        }

    def _fail_result(self, error, message, result, stdout, stderr, metrics, thresholds, reasons):
        return self.fail(
            error,
            message=message,
            stdout=(stdout or '').strip(),
            stderr=(stderr or '').strip(),
            metrics=metrics,
            thresholds=self._thresholds_for_result(thresholds),
            reasons=reasons,
        )

    def run(self):
        thresholds = self._load_thresholds()
        error_log_dir = str(thresholds.get('error_log_path') or '').rstrip('/') or '/'
        error_regex = self._build_error_regex(thresholds.get('error_keywords') or [])

        command = (
            'latest="$(ls ' + self._quote(error_log_dir) + '/error.log* 2>/dev/null | sort | tail -n 1)"; '
            'if [ -z "$latest" ]; then '
            "printf '%s\\n' " + self._quote(self.LOG_NOT_FOUND_MARKER) + '; '
            'echo ' + self.FAP_RC_MARKER + '2; '
            'else '
            "printf '%s\\n' " + self._quote(self.LATEST_LOG_MARKER) + '"$latest"; '
            'grep -Ei ' + self._quote(error_regex) + ' "$latest"; '
            'echo ' + self.FAP_RC_MARKER + '$?; '
            'fi'
        )

        result = self._run_command(command, timeout=self.DEFAULT_COMMAND_TIMEOUT)
        stdout = result.get('stdout') or ''
        stderr = result.get('stderr') or ''
        marker_rc = self._extract_marker_rc(stdout)
        latest_log_file = self._extract_latest_log_file(stdout)
        cleaned_stdout = self._remove_control_lines(stdout)

        try:
            compiled_error_regex = re.compile(error_regex, re.IGNORECASE)
            matched_lines = [
                line.strip()
                for line in cleaned_stdout.splitlines()
                if line.strip() and compiled_error_regex.search(line)
            ]
        except Exception:
            matched_lines = []

        metrics = self._base_metrics(
            result,
            stdout,
            stderr,
            thresholds,
            command,
            marker_rc=marker_rc,
            matched_lines=matched_lines,
            latest_log_file=latest_log_file,
        )

        if result.get('timed_out'):
            return self._fail_result(
                '점검 명령 timeout',
                '에러 로그 점검에 실패했습니다. 명령 실행 중 timeout이 발생하여 상태를 판단하지 못했습니다.',
                result,
                stdout,
                stderr,
                metrics,
                thresholds,
                '명령 timeout',
            )

        if result.get('rc') != 0:
            return self._fail_result(
                '점검 명령 실행 실패',
                '에러 로그 점검에 실패했습니다. Paramiko 명령 실행 결과가 비정상 종료되어 상태를 판단하지 못했습니다.',
                result,
                stdout,
                stderr,
                metrics,
                thresholds,
                'Paramiko 명령 실행 rc 비정상',
            )

        non_matching_stdout = self._stdout_without_matched_lines(cleaned_stdout, matched_lines)
        failure_keyword = self._contains_failure_keyword(stderr, non_matching_stdout)
        if failure_keyword:
            return self._fail_result(
                '점검 명령 실행 실패',
                '에러 로그 점검에 실패했습니다. 명령 출력에서 실행 실패 키워드가 확인되었습니다: {0}'.format(failure_keyword),
                result,
                stdout,
                stderr,
                metrics,
                thresholds,
                '명령 실패 키워드 확인: {0}'.format(failure_keyword),
            )

        if marker_rc is None:
            return self._fail_result(
                'marker rc 파싱 실패',
                '에러 로그 점검에 실패했습니다. grep 내부 종료코드 marker를 파싱하지 못해 상태를 판단하지 못했습니다.',
                result,
                stdout,
                stderr,
                metrics,
                thresholds,
                'marker rc 파싱 실패',
            )

        if self.LOG_NOT_FOUND_MARKER in stdout or not latest_log_file:
            return self._fail_result(
                'error log 파일 없음',
                '에러 로그 점검에 실패했습니다. error log 파일 없음, error log 경로 없음 또는 권한 문제로 최신 로그 파일을 확인하지 못했습니다.',
                result,
                stdout,
                stderr,
                metrics,
                thresholds,
                '최신 error log 파일 없음',
            )

        if marker_rc >= 2:
            return self._fail_result(
                'grep 실행 실패',
                '에러 로그 점검에 실패했습니다. grep 실행 오류 또는 권한 문제로 상태를 판단하지 못했습니다.',
                result,
                stdout,
                stderr,
                metrics,
                thresholds,
                'grep 내부 rc 비정상: {0}'.format(marker_rc),
            )

        if marker_rc == 1:
            message = (
                '에러 로그 점검 결과 정상입니다. 최신 로그 파일 {0}에서 {1} 에러가 확인되지 않았습니다.'
            ).format(
                latest_log_file,
                '/'.join(thresholds.get('error_keywords') or []),
            )
            return self.ok(
                metrics=metrics,
                thresholds=self._thresholds_for_result(thresholds),
                reasons='CRITICAL/FATAL 에러 없음',
                message=message,
            )

        if marker_rc != 0:
            return self._fail_result(
                'grep 결과 파싱 실패',
                '에러 로그 점검에 실패했습니다. grep 내부 종료코드가 예상 범위를 벗어나 상태를 판단하지 못했습니다.',
                result,
                stdout,
                stderr,
                metrics,
                thresholds,
                '예상하지 못한 marker rc: {0}'.format(marker_rc),
            )

        if not matched_lines:
            return self._fail_result(
                '출력 파싱 실패',
                '에러 로그 점검에 실패했습니다. grep 결과는 존재하지만 CRITICAL/FATAL 매칭 라인을 파싱하지 못했습니다.',
                result,
                stdout,
                stderr,
                metrics,
                thresholds,
                '출력 파싱 실패',
            )

        message = (
            '에러 로그 점검 결과 경고입니다. 최신 로그 파일 {0}에서 {1} 에러 로그가 {2}건 확인되었습니다.'
        ).format(
            latest_log_file,
            '/'.join(thresholds.get('error_keywords') or []),
            len(matched_lines),
        )
        return self.warn(
            metrics=metrics,
            thresholds=self._thresholds_for_result(thresholds),
            reasons='CRITICAL/FATAL 에러 로그 확인',
            message=message,
        )


CHECK_CLASS = Check
