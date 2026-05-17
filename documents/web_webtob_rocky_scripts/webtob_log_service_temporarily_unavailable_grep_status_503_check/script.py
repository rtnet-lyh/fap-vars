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

    def _quote(self, value):
        return shlex.quote(str(value or ''))

    def _get_failure_keywords(self):
        return self._split_csv(
            self.get_threshold_var(
                'failure_keywords',
                default=self.DEFAULT_FAILURE_KEYWORDS,
                value_type='str',
            )
        )

    def _contains_failure_keyword(self, *texts):
        combined = '\n'.join(str(text or '') for text in texts if text is not None)
        lowered = combined.lower()
        for keyword in self._get_failure_keywords():
            if keyword and keyword.lower() in lowered:
                return keyword
        return ''

    def _status_pattern(self, status_code):
        return r'(^|[^0-9]){0}([^0-9]|$)'.format(int(status_code))

    def _load_thresholds(self):
        error_log_path = self.get_threshold_var(
            'error_log_path',
            default='/home/exTMS/tmax/webtob/log/main',
            value_type='str',
        )
        service_unavailable_status_code = self.get_threshold_var(
            'service_unavailable_status_code',
            default=503,
            value_type='int',
        )
        sample_line_limit = self.get_threshold_var(
            'sample_line_limit',
            default=20,
            value_type='int',
        )
        failure_keywords = self._get_failure_keywords()

        try:
            service_unavailable_status_code = int(service_unavailable_status_code)
        except Exception:
            service_unavailable_status_code = 503

        try:
            sample_line_limit = int(sample_line_limit)
        except Exception:
            sample_line_limit = 20
        if sample_line_limit < 1:
            sample_line_limit = 1

        return {
            'error_log_path': str(error_log_path or '').strip(),
            'service_unavailable_status_code': service_unavailable_status_code,
            'sample_line_limit': sample_line_limit,
            'failure_keywords': failure_keywords,
        }

    def _build_command(self, error_log_path, status_code):
        log_dir = str(error_log_path or '').rstrip('/') or str(error_log_path or '')
        safe_log_glob = self._quote(log_dir) + '/error.log*'
        grep_pattern = self._status_pattern(status_code)
        safe_grep_pattern = self._quote(grep_pattern)

        return (
            'latest_log=$(ls {log_glob} 2>/dev/null | sort | tail -n 1); '
            'if [ -z "$latest_log" ]; then '
            'printf "%s\\n" "{not_found}"; '
            'printf "%s\\n" "{rc_marker}2"; '
            'else '
            'printf "%s\\n" "{latest_marker}${{latest_log}}"; '
            'grep -E {pattern} "$latest_log"; '
            'printf "%s\\n" "{rc_marker}$?"; '
            'fi'
        ).format(
            log_glob=safe_log_glob,
            not_found=self.LOG_NOT_FOUND_MARKER,
            rc_marker=self.FAP_RC_MARKER,
            latest_marker=self.LATEST_LOG_MARKER,
            pattern=safe_grep_pattern,
        )

    def _run_command(self, command, timeout=None):
        timeout = self.DEFAULT_COMMAND_TIMEOUT if timeout is None else timeout
        results = self._run_paramiko_commands(
            [{'command': command, 'timeout': timeout}],
            profile=self.PARAMIKO_PROFILE,
        )
        if not results:
            return {
                'command': command,
                'rc': 1,
                'stdout': '',
                'stderr': '\uba85\ub839 \uc2e4\ud589 \uacb0\uacfc\uac00 \ube44\uc5b4 \uc788\uc2b5\ub2c8\ub2e4.',
                'timed_out': False,
            }
        return results[0]

    def _extract_marker_rc(self, text):
        marker_pattern = re.escape(self.FAP_RC_MARKER) + r'(\d+)'
        match = re.search(marker_pattern, str(text or ''))
        if not match:
            return None
        try:
            return int(match.group(1))
        except Exception:
            return None

    def _extract_latest_log_file(self, text):
        marker_pattern = re.escape(self.LATEST_LOG_MARKER) + r'(.+)'
        for line in str(text or '').splitlines():
            match = re.search(marker_pattern, line.strip())
            if match:
                return match.group(1).strip()
        return ''

    def _remove_marker_lines(self, text):
        rc_pattern = re.escape(self.FAP_RC_MARKER) + r'\d+'
        latest_pattern = re.escape(self.LATEST_LOG_MARKER)
        lines = []
        for line in str(text or '').splitlines():
            stripped = line.strip()
            if re.search(rc_pattern, stripped):
                continue
            if stripped.startswith(self.LOG_NOT_FOUND_MARKER):
                continue
            if re.search(latest_pattern, stripped):
                continue
            lines.append(line)
        return '\n'.join(lines).strip()

    def _collect_status_lines(self, text, status_code):
        pattern = re.compile(self._status_pattern(status_code))
        matched_lines = []
        for line in str(text or '').splitlines():
            clean_line = line.strip()
            if clean_line and pattern.search(clean_line):
                matched_lines.append(clean_line)
        return matched_lines

    def _base_metrics(self, result, command, stdout, stderr, thresholds, marker_rc=None):
        return {
            'command': command,
            'command_rc': result.get('rc'),
            'timed_out': bool(result.get('timed_out', False)),
            'stdout_line_count': self._line_count(stdout),
            'stderr_line_count': self._line_count(stderr),
            'error_log_path': thresholds.get('error_log_path'),
            'latest_log_file': '',
            'service_unavailable_status_code': thresholds.get('service_unavailable_status_code'),
            'sample_line_limit': thresholds.get('sample_line_limit'),
            'marker_rc': marker_rc,
            'matched_count': 0,
            'sampled_lines': [],
            'first_matched_line': '',
            'has_service_unavailable_status': False,
        }

    def _failure_result(self, error, message, result, metrics, thresholds, stdout, stderr, reasons):
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
        status_code = thresholds.get('service_unavailable_status_code')
        sample_limit = thresholds.get('sample_line_limit')
        error_log_path = thresholds.get('error_log_path')

        command = ''
        result = {'rc': None, 'stdout': '', 'stderr': '', 'timed_out': False}
        stdout = ''
        stderr = ''
        metrics = self._base_metrics(result, command, stdout, stderr, thresholds)

        if not error_log_path:
            return self._failure_result(
                '\uc784\uacc4\uce58 \uc624\ub958',
                '\uc11c\ube44\uc2a4 \uc81c\uacf5 \ubd88\uac00 \uc810\uac80\uc5d0 \uc2e4\ud328\ud588\uc2b5\ub2c8\ub2e4. error_log_path \uac12\uc774 \ube44\uc5b4 \uc788\uc5b4 \uc0c1\ud0dc\ub97c \ud310\ub2e8\ud558\uc9c0 \ubabb\ud588\uc2b5\ub2c8\ub2e4.',
                result,
                metrics,
                thresholds,
                stdout,
                stderr,
                'error_log_path \uc784\uacc4\uce58\uac00 \ube44\uc5b4 \uc788\uc74c',
            )

        if not isinstance(status_code, int) or status_code < 100 or status_code > 599:
            return self._failure_result(
                '\uc784\uacc4\uce58 \uc624\ub958',
                '\uc11c\ube44\uc2a4 \uc81c\uacf5 \ubd88\uac00 \uc810\uac80\uc5d0 \uc2e4\ud328\ud588\uc2b5\ub2c8\ub2e4. service_unavailable_status_code \uac12\uc774 HTTP status code \ubc94\uc704(100~599)\uac00 \uc544\ub2d9\ub2c8\ub2e4.',
                result,
                metrics,
                thresholds,
                stdout,
                stderr,
                'service_unavailable_status_code \uc784\uacc4\uce58 \uac80\uc99d \uc2e4\ud328',
            )

        command = self._build_command(error_log_path, status_code)
        result = self._run_command(command, timeout=self.DEFAULT_COMMAND_TIMEOUT)
        stdout = result.get('stdout') or ''
        stderr = result.get('stderr') or ''
        marker_rc = self._extract_marker_rc(stdout)
        latest_log_file = self._extract_latest_log_file(stdout)
        grep_output = self._remove_marker_lines(stdout)
        matched_lines = self._collect_status_lines(grep_output, status_code)
        sampled_lines = matched_lines[:sample_limit]

        metrics = self._base_metrics(result, command, stdout, stderr, thresholds, marker_rc=marker_rc)
        metrics.update({
            'latest_log_file': latest_log_file,
            'matched_count': len(matched_lines),
            'sampled_lines': sampled_lines,
            'first_matched_line': matched_lines[0] if matched_lines else '',
            'has_service_unavailable_status': bool(matched_lines),
        })

        if result.get('timed_out'):
            return self._failure_result(
                '\uba85\ub839 timeout',
                '\uc11c\ube44\uc2a4 \uc81c\uacf5 \ubd88\uac00 \uc810\uac80\uc5d0 \uc2e4\ud328\ud588\uc2b5\ub2c8\ub2e4. \ucd5c\uc2e0 error log \ud30c\uc77c \ud655\uc778 \ub610\ub294 503 \uac80\uc0c9 \uba85\ub839\uc774 timeout\ub418\uc5b4 \uc0c1\ud0dc\ub97c \ud310\ub2e8\ud558\uc9c0 \ubabb\ud588\uc2b5\ub2c8\ub2e4.',
                result,
                metrics,
                thresholds,
                stdout,
                stderr,
                '\uba85\ub839 timeout',
            )

        if result.get('rc') != 0:
            return self._failure_result(
                '\uc810\uac80 \uba85\ub839 \uc2e4\ud589 \uc2e4\ud328',
                '\uc11c\ube44\uc2a4 \uc81c\uacf5 \ubd88\uac00 \uc810\uac80\uc5d0 \uc2e4\ud328\ud588\uc2b5\ub2c8\ub2e4. Paramiko \uba85\ub839 \uc885\ub8cc\ucf54\ub4dc\uac00 0\uc774 \uc544\ub2c8\uc5b4 \uc0c1\ud0dc\ub97c \ud310\ub2e8\ud558\uc9c0 \ubabb\ud588\uc2b5\ub2c8\ub2e4.',
                result,
                metrics,
                thresholds,
                stdout,
                stderr,
                'Paramiko \uba85\ub839 rc \ube44\uc815\uc0c1',
            )

        if self.LOG_NOT_FOUND_MARKER in stdout or marker_rc == 2 and not latest_log_file:
            return self._failure_result(
                'error log \ud30c\uc77c \uc5c6\uc74c',
                '\uc11c\ube44\uc2a4 \uc81c\uacf5 \ubd88\uac00 \uc810\uac80\uc5d0 \uc2e4\ud328\ud588\uc2b5\ub2c8\ub2e4. error log \ud30c\uc77c \uc5c6\uc74c, grep \uc2e4\ud589 \uc624\ub958, marker rc \ud30c\uc2f1 \uc2e4\ud328 \ub610\ub294 \ucd9c\ub825 \ud30c\uc2f1 \uc2e4\ud328\ub85c \uc0c1\ud0dc\ub97c \ud310\ub2e8\ud558\uc9c0 \ubabb\ud588\uc2b5\ub2c8\ub2e4.',
                result,
                metrics,
                thresholds,
                stdout,
                stderr,
                'error log \ud30c\uc77c \uc5c6\uc74c',
            )

        failure_keyword = self._contains_failure_keyword(stdout, stderr)
        if failure_keyword:
            return self._failure_result(
                '\uc810\uac80 \uba85\ub839 \uc2e4\ud589 \uc2e4\ud328',
                '\uc11c\ube44\uc2a4 \uc81c\uacf5 \ubd88\uac00 \uc810\uac80\uc5d0 \uc2e4\ud328\ud588\uc2b5\ub2c8\ub2e4. \ucd9c\ub825\uc5d0\uc11c \uba85\ub839 \uc2e4\ud589 \uc2e4\ud328 \ud0a4\uc6cc\ub4dc({0})\uac00 \ud655\uc778\ub418\uc5b4 \uc0c1\ud0dc\ub97c \ud310\ub2e8\ud558\uc9c0 \ubabb\ud588\uc2b5\ub2c8\ub2e4.'.format(failure_keyword),
                result,
                metrics,
                thresholds,
                stdout,
                stderr,
                '\uc2e4\ud328 \ud0a4\uc6cc\ub4dc \ud655\uc778: {0}'.format(failure_keyword),
            )

        if marker_rc is None:
            return self._failure_result(
                'marker rc \ud30c\uc2f1 \uc2e4\ud328',
                '\uc11c\ube44\uc2a4 \uc81c\uacf5 \ubd88\uac00 \uc810\uac80\uc5d0 \uc2e4\ud328\ud588\uc2b5\ub2c8\ub2e4. grep \ub0b4\ubd80 \uc885\ub8cc\ucf54\ub4dc marker\ub97c \ud30c\uc2f1\ud558\uc9c0 \ubabb\ud574 \uc0c1\ud0dc\ub97c \ud310\ub2e8\ud558\uc9c0 \ubabb\ud588\uc2b5\ub2c8\ub2e4.',
                result,
                metrics,
                thresholds,
                stdout,
                stderr,
                'marker rc \ud30c\uc2f1 \uc2e4\ud328',
            )

        if marker_rc >= 2:
            return self._failure_result(
                'grep \uc2e4\ud589 \uc624\ub958',
                '\uc11c\ube44\uc2a4 \uc81c\uacf5 \ubd88\uac00 \uc810\uac80\uc5d0 \uc2e4\ud328\ud588\uc2b5\ub2c8\ub2e4. grep \ub0b4\ubd80 \uc885\ub8cc\ucf54\ub4dc\uac00 {0}\uc774\uc5b4\uc11c \uc0c1\ud0dc\ub97c \ud310\ub2e8\ud558\uc9c0 \ubabb\ud588\uc2b5\ub2c8\ub2e4.'.format(marker_rc),
                result,
                metrics,
                thresholds,
                stdout,
                stderr,
                'grep marker rc \ube44\uc815\uc0c1: {0}'.format(marker_rc),
            )

        if not latest_log_file:
            return self._failure_result(
                '\ucd9c\ub825 \ud30c\uc2f1 \uc2e4\ud328',
                '\uc11c\ube44\uc2a4 \uc81c\uacf5 \ubd88\uac00 \uc810\uac80\uc5d0 \uc2e4\ud328\ud588\uc2b5\ub2c8\ub2e4. \ucd5c\uc2e0 error log \ud30c\uc77c \uacbd\ub85c\ub97c \ud30c\uc2f1\ud558\uc9c0 \ubabb\ud574 \uc0c1\ud0dc\ub97c \ud310\ub2e8\ud558\uc9c0 \ubabb\ud588\uc2b5\ub2c8\ub2e4.',
                result,
                metrics,
                thresholds,
                stdout,
                stderr,
                '\ucd5c\uc2e0 error log \ud30c\uc77c \uacbd\ub85c \ud30c\uc2f1 \uc2e4\ud328',
            )

        if marker_rc == 1:
            message = (
                '\uc11c\ube44\uc2a4 \uc81c\uacf5 \ubd88\uac00 \uc810\uac80 \uacb0\uacfc \uc815\uc0c1\uc785\ub2c8\ub2e4. '
                '\ucd5c\uc2e0 error log \ud30c\uc77c {0}\uc5d0\uc11c \uc0c1\ud0dc\ucf54\ub4dc {1} \ub85c\uadf8\uac00 \ud655\uc778\ub418\uc9c0 \uc54a\uc558\uc2b5\ub2c8\ub2e4.'
            ).format(latest_log_file, status_code)
            return self.ok(
                metrics=metrics,
                thresholds=thresholds,
                reasons='\uc0c1\ud0dc\ucf54\ub4dc {0} \ub85c\uadf8 \ubbf8\uac10\uc9c0'.format(status_code),
                message=message,
            )

        if marker_rc == 0:
            if not matched_lines:
                return self._failure_result(
                    '\ucd9c\ub825 \ud30c\uc2f1 \uc2e4\ud328',
                    '\uc11c\ube44\uc2a4 \uc81c\uacf5 \ubd88\uac00 \uc810\uac80\uc5d0 \uc2e4\ud328\ud588\uc2b5\ub2c8\ub2e4. grep\uc740 \ub9e4\uce6d \uacb0\uacfc\uac00 \uc788\ub2e4\uace0 \ubc18\ud658\ud588\uc9c0\ub9cc \uc0c1\ud0dc\ucf54\ub4dc \ub77c\uc778\uc744 \ud30c\uc2f1\ud558\uc9c0 \ubabb\ud588\uc2b5\ub2c8\ub2e4.',
                    result,
                    metrics,
                    thresholds,
                    stdout,
                    stderr,
                    '\ub9e4\uce6d \ub77c\uc778 \ud30c\uc2f1 \uc2e4\ud328',
                )

            message = (
                '\uc11c\ube44\uc2a4 \uc81c\uacf5 \ubd88\uac00 \uc810\uac80 \uacb0\uacfc \uacbd\uace0\uc785\ub2c8\ub2e4. '
                '\ucd5c\uc2e0 error log \ud30c\uc77c {0}\uc5d0\uc11c \uc0c1\ud0dc\ucf54\ub4dc {1} \ub85c\uadf8\uac00 {2}\uac74 \ud655\uc778\ub418\uc5c8\uc2b5\ub2c8\ub2e4.'
            ).format(latest_log_file, status_code, len(matched_lines))
            return self.warn(
                metrics=metrics,
                thresholds=thresholds,
                reasons='\uc0c1\ud0dc\ucf54\ub4dc {0} \ub85c\uadf8 {1}\uac74 \ud655\uc778'.format(status_code, len(matched_lines)),
                message=message,
            )

        return self._failure_result(
            'marker rc \ud30c\uc2f1 \uc2e4\ud328',
            '\uc11c\ube44\uc2a4 \uc81c\uacf5 \ubd88\uac00 \uc810\uac80\uc5d0 \uc2e4\ud328\ud588\uc2b5\ub2c8\ub2e4. grep marker rc \uac12\uc774 \uc608\uc0c1 \ubc94\uc704(0, 1, 2 \uc774\uc0c1)\ub85c \ud574\uc11d\ub418\uc9c0 \uc54a\uc544 \uc0c1\ud0dc\ub97c \ud310\ub2e8\ud558\uc9c0 \ubabb\ud588\uc2b5\ub2c8\ub2e4.',
            result,
            metrics,
            thresholds,
            stdout,
            stderr,
            '\uc608\uc0c1\ud558\uc9c0 \ubabb\ud55c marker rc: {0}'.format(marker_rc),
        )


CHECK_CLASS = Check
