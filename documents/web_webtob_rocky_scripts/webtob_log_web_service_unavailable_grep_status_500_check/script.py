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
    FAP_LATEST_LOG_MARKER = '__FAP_LATEST_LOG__'
    FAP_MATCHED_COUNT_MARKER = '__FAP_MATCHED_COUNT__'
    FAP_LOG_NOT_FOUND_MARKER = '__FAP_LOG_NOT_FOUND__'

    def _split_csv(self, raw_value):
        return [
            token.strip()
            for token in str(raw_value or '').split(',')
            if token.strip()
        ]

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
        combined = '\n'.join(str(text or '') for text in texts if text is not None)
        lowered = combined.lower()
        for keyword in self._get_failure_keywords():
            if keyword.lower() in lowered:
                return keyword
        return ''

    def _run_command(self, command, timeout=None):
        resolved_timeout = self.DEFAULT_COMMAND_TIMEOUT if timeout is None else timeout
        results = self._run_paramiko_commands(
            [
                {
                    'command': command,
                    'timeout': resolved_timeout,
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

    def _extract_marker_int(self, text, marker):
        pattern = re.escape(marker) + r'\s*(\d+)'
        match = re.search(pattern, str(text or ''))
        if not match:
            return None
        try:
            return int(match.group(1))
        except Exception:
            return None

    def _extract_marker_value(self, text, marker):
        for line in str(text or '').splitlines():
            if line.startswith(marker):
                return line[len(marker):].strip()
        return ''

    def _is_marker_line(self, line):
        text = str(line or '').strip()
        return (
            text.startswith(self.FAP_RC_MARKER)
            or text.startswith(self.FAP_LATEST_LOG_MARKER)
            or text.startswith(self.FAP_MATCHED_COUNT_MARKER)
            or text == self.FAP_LOG_NOT_FOUND_MARKER
        )

    def _extract_non_marker_lines(self, text):
        return [
            line.strip()
            for line in str(text or '').splitlines()
            if line.strip() and not self._is_marker_line(line)
        ]

    def _base_metrics(self, result, stdout=None, stderr=None):
        out = result.get('stdout') if stdout is None else stdout
        err = result.get('stderr') if stderr is None else stderr
        return {
            'command': result.get('command') or '',
            'command_rc': result.get('rc'),
            'timed_out': bool(result.get('timed_out', False)),
            'stdout_line_count': self._line_count(out),
            'stderr_line_count': self._line_count(err),
        }

    def _load_thresholds(self):
        error_log_path = self.get_threshold_var(
            'error_log_path',
            default='/home/exTMS/tmax/webtob/log/main',
            value_type='str',
        )
        status_code = self.get_threshold_var(
            'web_service_unavailable_status_code',
            default=500,
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
            'error_log_path': str(error_log_path or '').strip() or '/home/exTMS/tmax/webtob/log/main',
            'web_service_unavailable_status_code': status_code,
            'sample_line_limit': sample_line_limit,
            'failure_keywords': failure_keywords,
        }

    def _validate_status_code(self, status_code):
        try:
            code = int(status_code)
        except Exception:
            raise ValueError('web_service_unavailable_status_code 값이 정수가 아닙니다: {0}'.format(status_code))
        if code < 100 or code > 599:
            raise ValueError('web_service_unavailable_status_code 값이 HTTP 상태코드 범위를 벗어났습니다: {0}'.format(status_code))
        return code

    def _build_command(self, thresholds):
        error_log_path = thresholds['error_log_path'].rstrip('/') or '/'
        safe_error_log_path = self._quote(error_log_path)
        status_code = self._validate_status_code(thresholds['web_service_unavailable_status_code'])
        status_pattern = '(^|[^0-9]){0}([^0-9]|$)'.format(status_code)
        safe_status_pattern = self._quote(status_pattern)
        sample_line_limit = int(thresholds['sample_line_limit'])

        return (
            'latest_log=$(ls {path}/error.log* 2>/dev/null | sort | tail -n 1); '
            'if [ -z "$latest_log" ]; then '
            'echo {log_not_found}; '
            'echo {latest_marker}; '
            'echo {count_marker}0; '
            'echo {rc_marker}2; '
            'else '
            'echo {latest_marker}$latest_log; '
            'grep_count=$(grep -E -c {pattern} "$latest_log" 2>&1); '
            'grep_rc=$?; '
            'if [ "$grep_rc" -eq 0 ]; then '
            'echo {count_marker}$grep_count; '
            'grep -E {pattern} "$latest_log" | head -n {limit}; '
            'elif [ "$grep_rc" -eq 1 ]; then '
            'echo {count_marker}0; '
            'else '
            'echo "$grep_count"; '
            'fi; '
            'echo {rc_marker}$grep_rc; '
            'fi'
        ).format(
            path=safe_error_log_path,
            pattern=safe_status_pattern,
            limit=sample_line_limit,
            log_not_found=self.FAP_LOG_NOT_FOUND_MARKER,
            latest_marker=self.FAP_LATEST_LOG_MARKER,
            count_marker=self.FAP_MATCHED_COUNT_MARKER,
            rc_marker=self.FAP_RC_MARKER,
        )

    def _fail_result(self, title, message, result, metrics, thresholds, stdout, stderr, reasons):
        return self.fail(
            title,
            message=message,
            stdout=(stdout or '').strip(),
            stderr=(stderr or '').strip(),
            metrics=metrics,
            thresholds=thresholds,
            reasons=reasons,
        )

    def run(self):
        try:
            thresholds = self._load_thresholds()
            status_code = self._validate_status_code(thresholds['web_service_unavailable_status_code'])
        except Exception as exc:
            return self.fail(
                '임계치 오류',
                message='WEB 서비스 불가 점검에 실패했습니다. 임계치 값이 올바르지 않아 상태를 판단하지 못했습니다.',
                stdout='',
                stderr=str(exc),
                metrics={},
                thresholds={},
                reasons=str(exc),
            )

        command = self._build_command(thresholds)
        result = self._run_command(command, timeout=self.DEFAULT_COMMAND_TIMEOUT)
        out = (result.get('stdout') or '').strip()
        err = (result.get('stderr') or '').strip()

        latest_log_file = self._extract_marker_value(out, self.FAP_LATEST_LOG_MARKER)
        marker_rc = self._extract_marker_int(out, self.FAP_RC_MARKER)
        marker_matched_count = self._extract_marker_int(out, self.FAP_MATCHED_COUNT_MARKER)
        output_lines = self._extract_non_marker_lines(out)
        status_regex = re.compile(r'(^|[^0-9]){0}([^0-9]|$)'.format(re.escape(str(status_code))))
        sampled_lines = [line for line in output_lines if status_regex.search(line)]
        matched_count = marker_matched_count if marker_matched_count is not None else len(sampled_lines)
        sample_line_limit = int(thresholds['sample_line_limit'])
        sampled_lines = sampled_lines[:sample_line_limit]
        first_matched_line = sampled_lines[0] if sampled_lines else ''
        has_status = bool(matched_count and matched_count > 0)

        metrics = self._base_metrics(result, stdout=out, stderr=err)
        metrics.update({
            'command': command,
            'error_log_path': thresholds['error_log_path'],
            'latest_log_file': latest_log_file,
            'web_service_unavailable_status_code': status_code,
            'sample_line_limit': sample_line_limit,
            'marker_rc': marker_rc,
            'matched_count': matched_count,
            'sampled_lines': sampled_lines,
            'first_matched_line': first_matched_line,
            'has_web_service_unavailable_status': has_status,
        })

        if result.get('timed_out'):
            return self._fail_result(
                '점검 명령 timeout',
                'WEB 서비스 불가 점검에 실패했습니다. 최신 error log 파일에서 상태코드 {0} 로그를 확인하는 명령이 timeout 되었습니다.'.format(status_code),
                result,
                metrics,
                thresholds,
                out,
                err,
                '명령 timeout',
            )

        if result.get('rc') != 0:
            return self._fail_result(
                '점검 명령 실행 실패',
                'WEB 서비스 불가 점검에 실패했습니다. Paramiko 명령 실행 종료코드가 rc={0}입니다.'.format(result.get('rc')),
                result,
                metrics,
                thresholds,
                out,
                err,
                'Paramiko 명령 실행 실패',
            )

        if self.FAP_LOG_NOT_FOUND_MARKER in out:
            return self._fail_result(
                'error log 파일 없음',
                'WEB 서비스 불가 점검에 실패했습니다. error log 경로 {0}에서 error.log* 파일을 찾지 못해 상태를 판단하지 못했습니다.'.format(thresholds['error_log_path']),
                result,
                metrics,
                thresholds,
                out,
                err,
                'error log 파일 없음',
            )

        diagnostic_lines = [line for line in output_lines if not status_regex.search(line)]
        failure_keyword = self._contains_failure_keyword(err, '\n'.join(diagnostic_lines))
        if failure_keyword:
            return self._fail_result(
                '점검 명령 실행 실패',
                'WEB 서비스 불가 점검에 실패했습니다. 출력에서 명령 실패 키워드가 확인되어 상태를 판단하지 못했습니다: {0}'.format(failure_keyword),
                result,
                metrics,
                thresholds,
                out,
                err,
                '명령 실패 키워드 확인: {0}'.format(failure_keyword),
            )

        if marker_rc is None:
            return self._fail_result(
                'marker rc 파싱 실패',
                'WEB 서비스 불가 점검에 실패했습니다. grep 내부 종료코드 marker를 파싱하지 못해 상태를 판단하지 못했습니다.',
                result,
                metrics,
                thresholds,
                out,
                err,
                'marker rc 파싱 실패',
            )

        if marker_rc >= 2:
            return self._fail_result(
                'grep 실행 오류',
                'WEB 서비스 불가 점검에 실패했습니다. 최신 error log 파일에서 상태코드 {0} 로그를 검색하는 grep 명령이 실패했습니다.'.format(status_code),
                result,
                metrics,
                thresholds,
                out,
                err,
                'grep 내부 종료코드 rc={0}'.format(marker_rc),
            )

        if marker_matched_count is None:
            return self._fail_result(
                '출력 파싱 실패',
                'WEB 서비스 불가 점검에 실패했습니다. 상태코드 {0} 로그 건수 marker를 파싱하지 못했습니다.'.format(status_code),
                result,
                metrics,
                thresholds,
                out,
                err,
                'matched_count 파싱 실패',
            )

        if marker_rc == 0 and matched_count > 0 and not sampled_lines:
            return self._fail_result(
                '출력 파싱 실패',
                'WEB 서비스 불가 점검에 실패했습니다. grep 결과는 있으나 상태코드 {0} 샘플 라인을 파싱하지 못했습니다.'.format(status_code),
                result,
                metrics,
                thresholds,
                out,
                err,
                '검색 결과 샘플 라인 파싱 실패',
            )

        if marker_rc == 1:
            metrics['matched_count'] = 0
            metrics['sampled_lines'] = []
            metrics['first_matched_line'] = ''
            metrics['has_web_service_unavailable_status'] = False
            return self.ok(
                metrics=metrics,
                thresholds=thresholds,
                reasons='상태코드 {0} 로그 없음'.format(status_code),
                message='WEB 서비스 불가 점검 결과 정상입니다. 최신 error log 파일 {0}에서 상태코드 {1} 로그가 확인되지 않았습니다.'.format(latest_log_file, status_code),
            )

        if marker_rc == 0 and matched_count > 0:
            return self.warn(
                metrics=metrics,
                thresholds=thresholds,
                reasons='상태코드 {0} 로그 {1}건 확인'.format(status_code, matched_count),
                message='WEB 서비스 불가 점검 결과 경고입니다. 최신 error log 파일 {0}에서 상태코드 {1} 로그가 {2}건 확인되었습니다.'.format(latest_log_file, status_code, matched_count),
            )

        return self._fail_result(
            '출력 파싱 실패',
            'WEB 서비스 불가 점검에 실패했습니다. grep 내부 종료코드와 검색 결과를 해석하지 못했습니다.',
            result,
            metrics,
            thresholds,
            out,
            err,
            '출력 파싱 실패',
        )


CHECK_CLASS = Check
