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
    FAP_LOG_NOT_FOUND_MARKER = '__FAP_LOG_NOT_FOUND__'
    FAP_LATEST_LOG_MARKER = '__FAP_LATEST_LOG__'

    DEFAULT_FAILURE_KEYWORDS = (
        'command not found,not found,No such file,No such file or directory,'
        'Permission denied,cannot,Connection refused,No route to host,timed out,'
        'PARAMIKO_CONNECTION_ERROR,PARAMIKO_COMMAND_TIMEOUT'
    )

    def _split_csv(self, raw_value):
        return [
            token.strip()
            for token in str(raw_value or '').split(',')
            if token.strip()
        ]

    def _line_count(self, text):
        return len([line for line in str(text or '').splitlines() if line.strip()])

    def _get_failure_keywords(self):
        raw_value = self.get_threshold_var(
            'failure_keywords',
            default=self.DEFAULT_FAILURE_KEYWORDS,
            value_type='str',
        )
        return self._split_csv(raw_value)

    def _contains_failure_keyword(self, *texts):
        combined = '\n'.join(str(text or '') for text in texts if text is not None)
        lowered = combined.lower()
        for keyword in self._get_failure_keywords():
            if keyword and keyword.lower() in lowered:
                return keyword
        return ''

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

    def _extract_marker_rc(self, text):
        pattern = re.escape(self.FAP_RC_MARKER) + r'(\d+)'
        match = re.search(pattern, str(text or ''))
        if not match:
            return None
        try:
            return int(match.group(1))
        except Exception:
            return None

    def _extract_latest_log_file(self, text):
        for line in str(text or '').splitlines():
            stripped = line.strip()
            if stripped.startswith(self.FAP_LATEST_LOG_MARKER):
                return stripped[len(self.FAP_LATEST_LOG_MARKER):].strip()
        return ''

    def _strip_control_lines(self, text):
        marker_pattern = re.escape(self.FAP_RC_MARKER) + r'\d+'
        lines = []
        for line in str(text or '').splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if re.search(marker_pattern, stripped):
                continue
            if stripped == self.FAP_LOG_NOT_FOUND_MARKER:
                continue
            if stripped.startswith(self.FAP_LATEST_LOG_MARKER):
                continue
            lines.append(line)
        return lines

    def _line_has_status_code(self, line, status_code):
        parts = str(line or '').split()
        if len(parts) < 3:
            return False
        return parts[-3] == str(status_code)

    def _base_metrics(self, command, result, stdout, stderr, thresholds, marker_rc=None, latest_log_file='', matched_lines=None):
        matched_lines = matched_lines or []
        sampled_lines = matched_lines[:thresholds['sample_line_limit']]
        return {
            'command': command,
            'command_rc': result.get('rc'),
            'timed_out': bool(result.get('timed_out', False)),
            'stdout_line_count': self._line_count(stdout),
            'stderr_line_count': self._line_count(stderr),
            'access_log_path': thresholds['access_log_path'],
            'latest_log_file': latest_log_file,
            'success_status_code': thresholds['success_status_code'],
            'sample_line_limit': thresholds['sample_line_limit'],
            'marker_rc': marker_rc,
            'matched_count': len(matched_lines),
            'sampled_lines': sampled_lines,
            'first_matched_line': sampled_lines[0] if sampled_lines else '',
            'has_success_status': len(matched_lines) > 0,
        }

    def _load_thresholds(self):
        access_log_path = self.get_threshold_var(
            'access_log_path',
            default='/home/exTMS/tmax/webtob/log/main',
            value_type='str',
        )
        success_status_code = self.get_threshold_var(
            'success_status_code',
            default=200,
            value_type='int',
        )
        sample_line_limit = self.get_threshold_var(
            'sample_line_limit',
            default=20,
            value_type='int',
        )
        if sample_line_limit < 1:
            sample_line_limit = 1
        failure_keywords = self._get_failure_keywords()
        return {
            'access_log_path': str(access_log_path or '').strip() or '/home/exTMS/tmax/webtob/log/main',
            'success_status_code': success_status_code,
            'sample_line_limit': sample_line_limit,
            'failure_keywords': failure_keywords,
        }

    def _validate_status_code(self, status_code):
        try:
            value = int(status_code)
        except Exception:
            return None
        if value < 100 or value > 599:
            return None
        return value

    def _build_command(self, access_log_path, status_code):
        safe_path = shlex.quote(str(access_log_path or '').rstrip('/'))
        return (
            'latest_log=$(ls ' + safe_path + '/access.log* 2>/dev/null | sort | tail -n 1); '
            'if [ -z "$latest_log" ]; then '
            'echo ' + self.FAP_LOG_NOT_FOUND_MARKER + '; '
            'echo ' + self.FAP_LATEST_LOG_MARKER + '; '
            'echo ' + self.FAP_RC_MARKER + '1; '
            'else '
            'echo ' + self.FAP_LATEST_LOG_MARKER + '${latest_log}; '
            "awk '$(NF-2)==" + str(status_code) + " {print}' \"$latest_log\"; "
            'echo ' + self.FAP_RC_MARKER + '$?; '
            'fi'
        )

    def _fail_result(self, title, message, command, result, stdout, stderr, thresholds, marker_rc=None, latest_log_file='', matched_lines=None, reasons=''):
        metrics = self._base_metrics(
            command,
            result,
            stdout,
            stderr,
            thresholds,
            marker_rc=marker_rc,
            latest_log_file=latest_log_file,
            matched_lines=matched_lines,
        )
        return self.fail(
            title,
            message=message,
            stdout=(stdout or '').strip(),
            stderr=(stderr or '').strip(),
            metrics=metrics,
            thresholds=thresholds,
            reasons=reasons or title,
        )

    def run(self):
        thresholds = self._load_thresholds()
        status_code = self._validate_status_code(thresholds['success_status_code'])
        if status_code is None:
            empty_result = {
                'command': '',
                'rc': 1,
                'stdout': '',
                'stderr': 'success_status_code 값이 올바르지 않습니다.',
                'timed_out': False,
            }
            return self._fail_result(
                '임계치 오류',
                'Access Log HTTP 200 응답 점검에 실패했습니다. success_status_code 값이 HTTP 상태 코드 범위가 아닙니다.',
                '',
                empty_result,
                '',
                empty_result['stderr'],
                thresholds,
                reasons='success_status_code 값 오류',
            )

        thresholds['success_status_code'] = status_code
        command = self._build_command(thresholds['access_log_path'], status_code)
        result = self._run_command(command, timeout=self.DEFAULT_COMMAND_TIMEOUT)
        stdout = result.get('stdout') or ''
        stderr = result.get('stderr') or ''
        marker_rc = self._extract_marker_rc(stdout)
        latest_log_file = self._extract_latest_log_file(stdout)
        output_lines = self._strip_control_lines(stdout)
        matched_lines = [
            line for line in output_lines
            if self._line_has_status_code(line, status_code)
        ]

        if result.get('timed_out'):
            return self._fail_result(
                '점검 명령 timeout',
                'Access Log HTTP 200 응답 점검에 실패했습니다. 명령 실행 중 timeout이 발생하여 상태를 판단하지 못했습니다.',
                command,
                result,
                stdout,
                stderr,
                thresholds,
                marker_rc=marker_rc,
                latest_log_file=latest_log_file,
                matched_lines=matched_lines,
                reasons='명령 timeout',
            )

        if result.get('rc') != 0:
            return self._fail_result(
                '점검 명령 실행 실패',
                'Access Log HTTP 200 응답 점검에 실패했습니다. Paramiko 명령 실행 결과가 정상 종료되지 않았습니다.',
                command,
                result,
                stdout,
                stderr,
                thresholds,
                marker_rc=marker_rc,
                latest_log_file=latest_log_file,
                matched_lines=matched_lines,
                reasons='Paramiko 명령 실행 오류',
            )

        if self.FAP_LOG_NOT_FOUND_MARKER in stdout or not latest_log_file:
            return self._fail_result(
                'access log 파일 없음',
                'Access Log HTTP 200 응답 점검에 실패했습니다. access log 파일이 없어 상태를 판단하지 못했습니다.',
                command,
                result,
                stdout,
                stderr,
                thresholds,
                marker_rc=marker_rc,
                latest_log_file=latest_log_file,
                matched_lines=matched_lines,
                reasons='access log 파일 없음',
            )

        if marker_rc is None:
            return self._fail_result(
                'marker rc 파싱 실패',
                'Access Log HTTP 200 응답 점검에 실패했습니다. awk 내부 실행 결과 marker rc를 파싱하지 못했습니다.',
                command,
                result,
                stdout,
                stderr,
                thresholds,
                marker_rc=marker_rc,
                latest_log_file=latest_log_file,
                matched_lines=matched_lines,
                reasons='marker rc 파싱 실패',
            )

        if marker_rc != 0:
            return self._fail_result(
                'awk 실행 실패',
                'Access Log HTTP 200 응답 점검에 실패했습니다. awk 실행 오류로 상태를 판단하지 못했습니다.',
                command,
                result,
                stdout,
                stderr,
                thresholds,
                marker_rc=marker_rc,
                latest_log_file=latest_log_file,
                matched_lines=matched_lines,
                reasons='awk 내부 실행 오류',
            )

        failure_keyword = self._contains_failure_keyword(stderr)
        if failure_keyword:
            return self._fail_result(
                '점검 명령 실패 키워드 감지',
                'Access Log HTTP 200 응답 점검에 실패했습니다. 출력에서 명령 실패 키워드가 확인되어 상태를 판단하지 못했습니다.',
                command,
                result,
                stdout,
                stderr,
                thresholds,
                marker_rc=marker_rc,
                latest_log_file=latest_log_file,
                matched_lines=matched_lines,
                reasons='실패 키워드 감지: ' + str(failure_keyword),
            )

        if output_lines and not matched_lines:
            return self._fail_result(
                '출력 파싱 실패',
                'Access Log HTTP 200 응답 점검에 실패했습니다. awk 출력은 있으나 HTTP 상태 코드 위치를 파싱하지 못했습니다.',
                command,
                result,
                stdout,
                stderr,
                thresholds,
                marker_rc=marker_rc,
                latest_log_file=latest_log_file,
                matched_lines=matched_lines,
                reasons='출력 파싱 실패',
            )

        metrics = self._base_metrics(
            command,
            result,
            stdout,
            stderr,
            thresholds,
            marker_rc=marker_rc,
            latest_log_file=latest_log_file,
            matched_lines=matched_lines,
        )

        if matched_lines:
            return self.ok(
                metrics=metrics,
                thresholds=thresholds,
                reasons='HTTP ' + str(status_code) + ' 응답 로그 확인',
                message=(
                    'Access Log HTTP 200 응답 점검 결과 정상입니다. 최신 로그 파일 '
                    + latest_log_file
                    + '에서 HTTP '
                    + str(status_code)
                    + ' 응답 로그가 '
                    + str(len(matched_lines))
                    + '건 확인되었습니다.'
                ),
            )

        return self.warn(
            metrics=metrics,
            thresholds=thresholds,
            reasons='HTTP ' + str(status_code) + ' 응답 로그 미확인',
            message=(
                'Access Log HTTP 200 응답 점검 결과 경고입니다. 최신 로그 파일 '
                + latest_log_file
                + '에서 HTTP '
                + str(status_code)
                + ' 응답 로그가 확인되지 않았습니다.'
            ),
        )


CHECK_CLASS = Check
