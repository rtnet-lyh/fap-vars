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
    LATEST_LOG_MARKER = '__FAP_LATEST_LOG__'
    LOG_NOT_FOUND_MARKER = '__FAP_LOG_NOT_FOUND__'
    LOG_PATH_NOT_FOUND_MARKER = '__FAP_LOG_PATH_NOT_FOUND__'

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

    def _normalize_directory_path(self, path):
        text = str(path or '').strip()
        if not text:
            text = '/home/exTMS/tmax/webtob/log/main'
        if len(text) > 1:
            text = text.rstrip('/')
        return text or '/home/exTMS/tmax/webtob/log/main'

    def _get_failure_keywords(self):
        return self._split_csv(
            self.get_threshold_var(
                'failure_keywords',
                default=self.DEFAULT_FAILURE_KEYWORDS,
                value_type='str',
            )
        )

    def _contains_failure_keyword(self, *texts):
        failure_keywords = self._get_failure_keywords()
        combined = '\n'.join(str(text or '') for text in texts if text is not None)
        lowered = combined.lower()

        for keyword in failure_keywords:
            if keyword and keyword.lower() in lowered:
                return keyword
        return ''

    def _load_thresholds(self):
        access_log_path = self._normalize_directory_path(
            self.get_threshold_var(
                'access_log_path',
                default='/home/exTMS/tmax/webtob/log/main',
                value_type='str',
            )
        )

        not_found_status_code = self.get_threshold_var(
            'not_found_status_code',
            default=404,
            value_type='int',
        )

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
            'access_log_path': access_log_path,
            'not_found_status_code': not_found_status_code,
            'sample_line_limit': sample_line_limit,
            'failure_keywords': self._get_failure_keywords(),
        }

    def _is_valid_http_status_code(self, value):
        try:
            number = int(value)
        except Exception:
            return False
        return 100 <= number <= 599

    def _build_command(self, access_log_path, status_code):
        safe_access_log_path = shlex.quote(str(access_log_path))
        return (
            'if [ ! -d {path} ]; then '
            'echo "{path_not_found}"; '
            'echo "{latest_marker}"; '
            'echo "{rc_marker}1"; '
            'else '
            'latest_log=$(ls {path}/access.log* 2>/dev/null | sort | tail -n 1); '
            'if [ -z "$latest_log" ]; then '
            'echo "{log_not_found}"; '
            'echo "{latest_marker}"; '
            'echo "{rc_marker}1"; '
            'else '
            'echo "{latest_marker}$latest_log"; '
            'awk \'$(NF-2)=={status_code} {{print}}\' "$latest_log"; '
            'echo "{rc_marker}$?"; '
            'fi; '
            'fi'
        ).format(
            path=safe_access_log_path,
            path_not_found=self.LOG_PATH_NOT_FOUND_MARKER,
            log_not_found=self.LOG_NOT_FOUND_MARKER,
            latest_marker=self.LATEST_LOG_MARKER,
            rc_marker=self.FAP_RC_MARKER,
            status_code=int(status_code),
        )

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
        matches = re.findall(pattern, str(text or ''))
        if not matches:
            return None
        try:
            return int(matches[-1])
        except Exception:
            return None

    def _extract_latest_log_file(self, text):
        for line in str(text or '').splitlines():
            if line.startswith(self.LATEST_LOG_MARKER):
                return line[len(self.LATEST_LOG_MARKER):].strip()
        return ''

    def _remove_control_lines(self, text):
        cleaned = []
        for line in str(text or '').splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith(self.FAP_RC_MARKER):
                continue
            if stripped.startswith(self.LATEST_LOG_MARKER):
                continue
            if stripped in (self.LOG_NOT_FOUND_MARKER, self.LOG_PATH_NOT_FOUND_MARKER):
                continue
            cleaned.append(line)
        return '\n'.join(cleaned).strip()

    def _line_has_status_code(self, line, status_code):
        fields = str(line or '').split()
        if len(fields) < 3:
            return False
        try:
            return int(fields[-3]) == int(status_code)
        except Exception:
            return False

    def _base_metrics(self, command, result, stdout, stderr):
        return {
            'command': command,
            'command_rc': result.get('rc'),
            'timed_out': bool(result.get('timed_out', False)),
            'stdout_line_count': self._line_count(stdout),
            'stderr_line_count': self._line_count(stderr),
            'access_log_path': '',
            'latest_log_file': '',
            'not_found_status_code': None,
            'sample_line_limit': None,
            'marker_rc': None,
            'matched_count': 0,
            'sampled_lines': [],
            'first_matched_line': '',
            'has_not_found_status': False,
        }

    def _fail_result(self, error, message, result, stdout, stderr, metrics, thresholds, reasons):
        return self.fail(
            error,
            message=message,
            stdout=(stdout or '').strip(),
            stderr=(stderr or '').strip(),
            metrics=metrics,
            thresholds=thresholds,
            reasons=', '.join(reasons) if isinstance(reasons, list) else str(reasons or ''),
        )

    def run(self):
        thresholds = self._load_thresholds()
        access_log_path = thresholds['access_log_path']
        not_found_status_code = thresholds['not_found_status_code']
        sample_line_limit = thresholds['sample_line_limit']

        if not self._is_valid_http_status_code(not_found_status_code):
            command = ''
            result = {
                'command': command,
                'rc': 1,
                'stdout': '',
                'stderr': '',
                'timed_out': False,
            }
            metrics = self._base_metrics(command, result, '', '')
            metrics.update({
                'access_log_path': access_log_path,
                'not_found_status_code': not_found_status_code,
                'sample_line_limit': sample_line_limit,
            })
            return self._fail_result(
                '임계치 오류',
                (
                    '요청 문서 처리 불가 점검에 실패했습니다. '
                    'not_found_status_code 값이 HTTP status code 범위(100~599)에 해당하지 않습니다.'
                ),
                result,
                '',
                '',
                metrics,
                thresholds,
                ['not_found_status_code 임계치 오류'],
            )

        command = self._build_command(access_log_path, int(not_found_status_code))
        result = self._run_command(command, timeout=self.DEFAULT_COMMAND_TIMEOUT)
        stdout = result.get('stdout') or ''
        stderr = result.get('stderr') or ''

        metrics = self._base_metrics(command, result, stdout, stderr)
        metrics.update({
            'access_log_path': access_log_path,
            'not_found_status_code': int(not_found_status_code),
            'sample_line_limit': sample_line_limit,
        })

        if result.get('timed_out'):
            return self._fail_result(
                '점검 명령 timeout',
                (
                    '요청 문서 처리 불가 점검에 실패했습니다. '
                    '최신 access log 파일 확인 또는 awk 실행 중 timeout이 발생했습니다.'
                ),
                result,
                stdout,
                stderr,
                metrics,
                thresholds,
                ['명령 timeout'],
            )

        if result.get('rc') != 0:
            return self._fail_result(
                '점검 명령 실행 실패',
                (
                    '요청 문서 처리 불가 점검에 실패했습니다. '
                    'Paramiko 명령 실행 종료코드가 정상 범위가 아니어서 상태를 판단하지 못했습니다.'
                ),
                result,
                stdout,
                stderr,
                metrics,
                thresholds,
                ['Paramiko 명령 실행 실패'],
            )

        marker_rc = self._extract_marker_rc(stdout)
        latest_log_file = self._extract_latest_log_file(stdout)
        clean_output = self._remove_control_lines(stdout)
        raw_match_lines = [
            line.strip()
            for line in clean_output.splitlines()
            if line.strip()
        ]
        matched_lines = [
            line for line in raw_match_lines
            if self._line_has_status_code(line, int(not_found_status_code))
        ]
        unparsed_lines = [
            line for line in raw_match_lines
            if not self._line_has_status_code(line, int(not_found_status_code))
        ]

        sampled_lines = matched_lines[:sample_line_limit]
        metrics.update({
            'latest_log_file': latest_log_file,
            'marker_rc': marker_rc,
            'matched_count': len(matched_lines),
            'sampled_lines': sampled_lines,
            'first_matched_line': matched_lines[0] if matched_lines else '',
            'has_not_found_status': bool(matched_lines),
        })

        if marker_rc is None:
            return self._fail_result(
                'marker rc 파싱 실패',
                (
                    '요청 문서 처리 불가 점검에 실패했습니다. '
                    'awk 실행 결과의 __FAP_RC__ marker를 파싱하지 못해 상태를 판단하지 못했습니다.'
                ),
                result,
                stdout,
                stderr,
                metrics,
                thresholds,
                ['marker rc 파싱 실패'],
            )

        if self.LOG_PATH_NOT_FOUND_MARKER in stdout:
            return self._fail_result(
                'access log 경로 없음',
                (
                    '요청 문서 처리 불가 점검에 실패했습니다. '
                    'access log 경로가 존재하지 않아 최신 access log 파일을 확인하지 못했습니다.'
                ),
                result,
                stdout,
                stderr,
                metrics,
                thresholds,
                ['access log 경로 없음'],
            )

        if self.LOG_NOT_FOUND_MARKER in stdout:
            return self._fail_result(
                'access log 파일 없음',
                (
                    '요청 문서 처리 불가 점검에 실패했습니다. '
                    'access log 파일 없음, awk 실행 오류, marker rc 파싱 실패 또는 출력 파싱 실패로 상태를 판단하지 못했습니다.'
                ),
                result,
                stdout,
                stderr,
                metrics,
                thresholds,
                ['access log 파일 없음'],
            )

        diagnostic_stdout = '\n'.join(unparsed_lines)
        failure_keyword = self._contains_failure_keyword(diagnostic_stdout, stderr)
        if failure_keyword:
            return self._fail_result(
                '점검 명령 실행 실패',
                (
                    '요청 문서 처리 불가 점검에 실패했습니다. '
                    '명령 출력에서 실행 실패 키워드가 확인되어 상태를 판단하지 못했습니다.'
                ),
                result,
                stdout,
                stderr,
                metrics,
                thresholds,
                ['실패 키워드 확인: {0}'.format(failure_keyword)],
            )

        if marker_rc != 0:
            return self._fail_result(
                'awk 실행 실패',
                (
                    '요청 문서 처리 불가 점검에 실패했습니다. '
                    'awk 실행 오류로 최신 access log의 HTTP 상태코드 로그를 확인하지 못했습니다.'
                ),
                result,
                stdout,
                stderr,
                metrics,
                thresholds,
                ['awk marker rc 비정상: {0}'.format(marker_rc)],
            )

        if raw_match_lines and unparsed_lines:
            return self._fail_result(
                '출력 파싱 실패',
                (
                    '요청 문서 처리 불가 점검에 실패했습니다. '
                    'awk 출력에서 HTTP 상태코드 필드를 파싱하지 못한 라인이 있어 상태를 판단하지 못했습니다.'
                ),
                result,
                stdout,
                stderr,
                metrics,
                thresholds,
                ['출력 파싱 실패'],
            )

        if not matched_lines:
            return self.ok(
                metrics=metrics,
                thresholds=thresholds,
                reasons='HTTP {0} 응답 로그 없음'.format(int(not_found_status_code)),
                message=(
                    '요청 문서 처리 불가 점검 결과 정상입니다. '
                    '최신 access log 파일 {0}에서 HTTP {1} 응답 로그가 확인되지 않았습니다.'
                ).format(latest_log_file, int(not_found_status_code)),
            )

        return self.warn(
            metrics=metrics,
            thresholds=thresholds,
            reasons='HTTP {0} 응답 로그 {1}건 확인'.format(
                int(not_found_status_code),
                len(matched_lines),
            ),
            message=(
                '요청 문서 처리 불가 점검 결과 경고입니다. '
                '최신 access log 파일 {0}에서 HTTP {1} 응답 로그가 {2}건 확인되었습니다.'
            ).format(
                latest_log_file,
                int(not_found_status_code),
                len(matched_lines),
            ),
        )


CHECK_CLASS = Check
