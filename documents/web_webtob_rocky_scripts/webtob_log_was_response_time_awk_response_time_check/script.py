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

    def _number_text(self, value):
        try:
            return ('%g' % float(value))
        except Exception:
            return str(value)

    def _metric_number(self, value):
        if value is None:
            return None
        try:
            number = float(value)
        except Exception:
            return None
        if number.is_integer():
            return int(number)
        return number

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
            if keyword.lower() in lowered:
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

    def _load_thresholds(self):
        access_log_path = self.get_threshold_var(
            'access_log_path',
            default='/home/exTMS/tmax/webtob/log/main',
            value_type='str',
        )
        max_response_time = self.get_threshold_var(
            'max_response_time',
            default=1000,
            value_type='float',
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
            'max_response_time': max_response_time,
            'sample_line_limit': sample_line_limit,
            'failure_keywords': failure_keywords,
        }

    def _build_command(self, access_log_path, max_response_time):
        safe_access_log_path = self._quote(str(access_log_path or '').rstrip('/'))
        threshold_text = self._number_text(max_response_time)
        awk_program = shlex.quote('$NF >= ' + threshold_text + ' {print}')
        return (
            'access_dir=' + safe_access_log_path + '; '
            'latest_log=$(ls "${access_dir}"/access.log* 2>/dev/null | sort | tail -n 1); '
            'if [ -z "$latest_log" ]; then '
            'latest_log=$(ls "${access_dir}"/main/access.log* 2>/dev/null | sort | tail -n 1); '
            'fi; '
            'if [ -z "$latest_log" ]; then '
            'echo ' + self.FAP_LOG_NOT_FOUND_MARKER + '; '
            'echo ' + self.FAP_RC_MARKER + '1; '
            'else '
            'echo "' + self.FAP_LATEST_LOG_MARKER + '${latest_log}"; '
            'awk ' + awk_program + ' "$latest_log"; '
            'echo ' + self.FAP_RC_MARKER + '$?; '
            'fi'
        )

    def _extract_command_output(self, stdout):
        marker_rc = None
        latest_log_file = ''
        log_not_found = False
        data_lines = []
        control_lines = []
        rc_pattern = re.compile(re.escape(self.FAP_RC_MARKER) + r'(\d+)')

        for raw_line in str(stdout or '').splitlines():
            line = raw_line.strip()
            if not line:
                continue

            rc_match = rc_pattern.search(line)
            if rc_match:
                try:
                    marker_rc = int(rc_match.group(1))
                except Exception:
                    marker_rc = None
                control_lines.append(line)
                continue

            if line.startswith(self.FAP_LATEST_LOG_MARKER):
                latest_log_file = line[len(self.FAP_LATEST_LOG_MARKER):].strip()
                control_lines.append(line)
                continue

            if self.FAP_LOG_NOT_FOUND_MARKER in line:
                log_not_found = True
                control_lines.append(line)
                continue

            data_lines.append(line)

        return {
            'marker_rc': marker_rc,
            'latest_log_file': latest_log_file,
            'log_not_found': log_not_found,
            'data_lines': data_lines,
            'control_lines': control_lines,
        }

    def _parse_response_lines(self, lines, max_response_time):
        matched_lines = []
        unparsed_lines = []
        below_threshold_lines = []
        response_times = []

        for line in lines:
            parts = str(line or '').rsplit(None, 1)
            if not parts:
                unparsed_lines.append(line)
                continue
            response_text = parts[-1]
            try:
                response_time = float(response_text)
            except Exception:
                unparsed_lines.append(line)
                continue

            if response_time >= max_response_time:
                matched_lines.append(line)
                response_times.append(response_time)
            else:
                below_threshold_lines.append(line)

        return {
            'matched_lines': matched_lines,
            'unparsed_lines': unparsed_lines,
            'below_threshold_lines': below_threshold_lines,
            'response_times': response_times,
        }

    def _base_metrics(self, result, command, stdout, stderr, thresholds, marker_rc=None, latest_log_file='', matched_lines=None, max_observed_response_time=None):
        matched_lines = matched_lines or []
        sample_line_limit = thresholds['sample_line_limit']
        sampled_lines = matched_lines[:sample_line_limit]
        return {
            'command': command,
            'command_rc': result.get('rc') if isinstance(result, dict) else None,
            'timed_out': bool(result.get('timed_out', False)) if isinstance(result, dict) else False,
            'stdout_line_count': self._line_count(stdout),
            'stderr_line_count': self._line_count(stderr),
            'access_log_path': thresholds['access_log_path'],
            'latest_log_file': latest_log_file or '',
            'max_response_time': thresholds['max_response_time'],
            'sample_line_limit': sample_line_limit,
            'marker_rc': marker_rc,
            'matched_count': len(matched_lines),
            'sampled_lines': sampled_lines,
            'first_matched_line': sampled_lines[0] if sampled_lines else '',
            'max_observed_response_time': self._metric_number(max_observed_response_time),
            'has_slow_response': bool(matched_lines),
        }

    def _fail_result(self, error, message, result, stdout, stderr, metrics, thresholds, reasons):
        return self.fail(
            error,
            message=message,
            stdout=(stdout or '').strip(),
            stderr=(stderr or '').strip(),
            metrics=metrics,
            thresholds=thresholds,
            reasons=reasons,
        )

    def run(self):
        thresholds = self._load_thresholds()
        max_response_time = thresholds['max_response_time']
        max_response_time_text = self._number_text(max_response_time)

        if max_response_time <= 0:
            metrics = self._base_metrics(
                {},
                '',
                '',
                '',
                thresholds,
            )
            return self.fail(
                '임계치 오류',
                message='WAS 응답시간 점검에 실패했습니다. max_response_time 값은 0보다 큰 숫자여야 합니다.',
                stdout='',
                stderr='',
                metrics=metrics,
                thresholds=thresholds,
                reasons='max_response_time 값이 올바르지 않습니다.',
            )

        command = self._build_command(thresholds['access_log_path'], max_response_time)
        result = self._run_command(command, timeout=self.DEFAULT_COMMAND_TIMEOUT)
        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()
        extracted = self._extract_command_output(stdout)
        marker_rc = extracted['marker_rc']
        latest_log_file = extracted['latest_log_file']
        data_lines = extracted['data_lines']
        parsed = self._parse_response_lines(data_lines, max_response_time)
        matched_lines = parsed['matched_lines']
        response_times = parsed['response_times']
        max_observed_response_time = max(response_times) if response_times else None

        metrics = self._base_metrics(
            result,
            command,
            stdout,
            stderr,
            thresholds,
            marker_rc=marker_rc,
            latest_log_file=latest_log_file,
            matched_lines=matched_lines,
            max_observed_response_time=max_observed_response_time,
        )

        if result.get('timed_out'):
            return self._fail_result(
                '점검 명령 timeout',
                'WAS 응답시간 점검에 실패했습니다. 원격 명령 실행 중 timeout이 발생했습니다.',
                result,
                stdout,
                stderr,
                metrics,
                thresholds,
                '명령 timeout으로 상태를 판단하지 못했습니다.',
            )

        if result.get('rc') != 0:
            return self._fail_result(
                '점검 명령 실행 실패',
                'WAS 응답시간 점검에 실패했습니다. 원격 명령 실행 종료코드가 정상 상태가 아닙니다.',
                result,
                stdout,
                stderr,
                metrics,
                thresholds,
                '원격 명령 실행 실패로 상태를 판단하지 못했습니다.',
            )

        if marker_rc is None:
            return self._fail_result(
                'marker rc 파싱 실패',
                'WAS 응답시간 점검에 실패했습니다. marker rc 파싱 실패로 상태를 판단하지 못했습니다.',
                result,
                stdout,
                stderr,
                metrics,
                thresholds,
                'marker rc 파싱 실패',
            )

        if extracted['log_not_found']:
            return self._fail_result(
                'access log 파일 없음',
                'WAS 응답시간 점검에 실패했습니다. access log 파일이 없어 상태를 판단하지 못했습니다.',
                result,
                stdout,
                stderr,
                metrics,
                thresholds,
                'access log 파일 없음',
            )

        if marker_rc != 0:
            return self._fail_result(
                'awk 실행 실패',
                'WAS 응답시간 점검에 실패했습니다. awk 실행 오류로 상태를 판단하지 못했습니다.',
                result,
                stdout,
                stderr,
                metrics,
                thresholds,
                'awk 실행 실패 또는 access log 읽기 실패',
            )

        failure_keyword = self._contains_failure_keyword(
            stderr,
            '\n'.join(extracted['control_lines']),
            '\n'.join(parsed['unparsed_lines']),
        )
        if failure_keyword:
            return self._fail_result(
                '점검 명령 실행 실패',
                'WAS 응답시간 점검에 실패했습니다. 명령 출력에서 실패 키워드가 확인되어 상태를 판단하지 못했습니다.',
                result,
                stdout,
                stderr,
                metrics,
                thresholds,
                '실패 키워드 확인: ' + failure_keyword,
            )

        if parsed['unparsed_lines']:
            metrics['unparsed_lines'] = parsed['unparsed_lines'][:thresholds['sample_line_limit']]
            return self._fail_result(
                '출력 파싱 실패',
                'WAS 응답시간 점검에 실패했습니다. 출력 파싱 실패로 상태를 판단하지 못했습니다.',
                result,
                stdout,
                stderr,
                metrics,
                thresholds,
                '응답시간 숫자를 파싱하지 못한 출력 라인이 있습니다.',
            )

        if parsed['below_threshold_lines']:
            metrics['below_threshold_lines'] = parsed['below_threshold_lines'][:thresholds['sample_line_limit']]
            return self._fail_result(
                '출력 파싱 실패',
                'WAS 응답시간 점검에 실패했습니다. awk 결과에 기준 미만 응답시간 라인이 포함되어 상태를 판단하지 못했습니다.',
                result,
                stdout,
                stderr,
                metrics,
                thresholds,
                'awk 출력과 max_response_time 기준이 일치하지 않습니다.',
            )

        if matched_lines and not response_times:
            return self._fail_result(
                '출력 파싱 실패',
                'WAS 응답시간 점검에 실패했습니다. 느린 응답 로그는 있으나 응답시간 숫자를 파싱하지 못했습니다.',
                result,
                stdout,
                stderr,
                metrics,
                thresholds,
                '응답시간 숫자 파싱 실패',
            )

        if matched_lines:
            observed_text = self._number_text(max_observed_response_time)
            message = (
                'WAS 응답시간 점검 결과 경고입니다. 최신 access log 파일 '
                + latest_log_file
                + '에서 응답시간 '
                + max_response_time_text
                + 'ms 이상 로그가 '
                + str(len(matched_lines))
                + '건 확인되었습니다. 최대 응답시간은 '
                + observed_text
                + 'ms입니다.'
            )
            return self.warn(
                metrics=metrics,
                thresholds=thresholds,
                reasons='응답시간 기준 이상 로그 확인',
                message=message,
            )

        message = (
            'WAS 응답시간 점검 결과 정상입니다. 최신 access log 파일 '
            + latest_log_file
            + '에서 응답시간 '
            + max_response_time_text
            + 'ms 이상 로그가 확인되지 않았습니다.'
        )
        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='응답시간 기준 이상 로그 없음',
            message=message,
        )


CHECK_CLASS = Check
