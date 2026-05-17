# -*- coding: utf-8 -*-

import re
import shlex

from .common._base import BaseCheck


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'linux'
    PARAMIKO_REUSE_SESSION = False

    DEFAULT_COMMAND_TIMEOUT = 15
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
        return len([
            line
            for line in str(text or '').splitlines()
            if line.strip()
        ])

    def _quote(self, value):
        return shlex.quote(str(value or ''))

    def _get_failure_keywords(self):
        raw_keywords = self.get_threshold_var(
            'failure_keywords',
            default=self.DEFAULT_FAILURE_KEYWORDS,
            value_type='str',
        )
        return self._split_csv(raw_keywords)

    def _contains_failure_keyword(self, *texts):
        combined = '\n'.join(str(text or '') for text in texts if text is not None)
        lowered = combined.lower()
        for keyword in self._get_failure_keywords():
            if keyword and keyword.lower() in lowered:
                return keyword
        return ''

    def _run_command(self, command, timeout):
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
        webtob_ctl_command = self.get_threshold_var(
            'webtob_ctl_command',
            default='webtob_ctl',
            value_type='str',
        )
        connection_status = self.get_threshold_var(
            'connection_status',
            default='RUNNING',
            value_type='str',
        )

        return {
            'webtob_ctl_command': webtob_ctl_command,
            'connection_status': connection_status,
            'failure_keywords': self._get_failure_keywords(),
        }

    def _extract_key_line(self, text, key):
        pattern = re.compile(r'^\s*' + re.escape(key) + r'\s*:\s*(.*?)\s*$', re.IGNORECASE)
        for line in str(text or '').splitlines():
            match = pattern.match(line)
            if match:
                return line.strip(), match.group(1).strip()
        return '', ''

    def _parse_int_value(self, value):
        match = re.search(r'-?\d+', str(value or ''))
        if not match:
            return None
        try:
            return int(match.group(0))
        except Exception:
            return None

    def _parse_status_output(self, text):
        status_line, status_value = self._extract_key_line(text, 'Status')
        max_connections_line, max_connections_value = self._extract_key_line(text, 'MaxConnections')
        max_request_line, max_request_value = self._extract_key_line(text, 'MaxRequestPerConnection')
        max_worker_line, max_worker_value = self._extract_key_line(text, 'MaxWorkerThreads')

        return {
            'status_line': status_line,
            'actual_status': status_value.strip(),
            'max_connections': self._parse_int_value(max_connections_value),
            'max_request_per_connection': self._parse_int_value(max_request_value),
            'max_worker_threads': self._parse_int_value(max_worker_value),
            'max_connections_line': max_connections_line,
            'max_request_per_connection_line': max_request_line,
            'max_worker_threads_line': max_worker_line,
        }

    def _build_metrics(self, command, result, stdout, stderr, expected_status, parsed=None):
        parsed = parsed or {}
        return {
            'command': command,
            'command_rc': result.get('rc'),
            'timed_out': bool(result.get('timed_out', False)),
            'stdout_line_count': self._line_count(stdout),
            'stderr_line_count': self._line_count(stderr),
            'expected_status': str(expected_status or '').strip(),
            'actual_status': parsed.get('actual_status') or '',
            'status_line': parsed.get('status_line') or '',
            'max_connections': parsed.get('max_connections'),
            'max_request_per_connection': parsed.get('max_request_per_connection'),
            'max_worker_threads': parsed.get('max_worker_threads'),
        }

    def _fail_result(self, title, message, stdout, stderr, metrics, thresholds, reasons):
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
        thresholds = self._load_thresholds()
        webtob_ctl_command = thresholds['webtob_ctl_command']
        expected_status = str(thresholds['connection_status'] or '').strip()
        command = f'{self._quote(webtob_ctl_command)} status'
        result = self._run_command(command, timeout=self.DEFAULT_COMMAND_TIMEOUT)

        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()
        parsed = {}
        metrics = self._build_metrics(command, result, stdout, stderr, expected_status, parsed)

        if result.get('timed_out'):
            return self._fail_result(
                'WEB-WAS 연동상태 점검 timeout',
                (
                    'WEB-WAS 연동상태 점검에 실패했습니다. '
                    'webtob_ctl status 명령 실행 중 timeout이 발생하여 상태를 판단하지 못했습니다.'
                ),
                stdout,
                stderr,
                metrics,
                thresholds,
                'webtob_ctl status 명령이 지정된 15초 안에 완료되지 않았습니다.',
            )

        rc = result.get('rc')
        if rc != 0:
            return self._fail_result(
                'WEB-WAS 연동상태 점검 명령 실행 실패',
                (
                    'WEB-WAS 연동상태 점검에 실패했습니다. '
                    'webtob_ctl status 명령 실행 오류로 상태를 판단하지 못했습니다.'
                ),
                stdout,
                stderr,
                metrics,
                thresholds,
                f'명령 종료코드가 rc={rc}입니다.',
            )

        failure_keyword = self._contains_failure_keyword(stdout, stderr)
        if failure_keyword:
            return self._fail_result(
                'WEB-WAS 연동상태 점검 명령 실행 실패',
                (
                    'WEB-WAS 연동상태 점검에 실패했습니다. '
                    'webtob_ctl status 명령 실행 오류 또는 실행 불가 메시지가 확인되었습니다.'
                ),
                stdout,
                stderr,
                metrics,
                thresholds,
                f'출력에서 실패 키워드가 확인되었습니다: {failure_keyword}',
            )

        if not stdout:
            return self._fail_result(
                'WEB-WAS 연동상태 점검 출력 없음',
                (
                    'WEB-WAS 연동상태 점검에 실패했습니다. '
                    'webtob_ctl status 명령 출력이 비어 있어 상태를 판단하지 못했습니다.'
                ),
                stdout,
                stderr,
                metrics,
                thresholds,
                '명령은 완료되었으나 stdout 출력이 없습니다.',
            )

        parsed = self._parse_status_output(stdout)
        metrics = self._build_metrics(command, result, stdout, stderr, expected_status, parsed)
        actual_status = parsed.get('actual_status') or ''

        if not actual_status:
            return self._fail_result(
                'WEB-WAS 연동상태 점검 Status 파싱 실패',
                (
                    'WEB-WAS 연동상태 점검에 실패했습니다. '
                    'webtob_ctl status 명령 실행 오류 또는 Status 파싱 실패로 상태를 판단하지 못했습니다.'
                ),
                stdout,
                stderr,
                metrics,
                thresholds,
                '출력에서 Status: 라인을 찾지 못했습니다.',
            )

        expected_normalized = expected_status.strip().lower()
        actual_normalized = actual_status.strip().lower()

        if actual_normalized == expected_normalized:
            return self.ok(
                metrics=metrics,
                thresholds=thresholds,
                reasons=(
                    f'파싱한 Status={actual_status} 값이 기대 상태 '
                    f'{expected_status}와 일치합니다.'
                ),
                message=(
                    f'WEB-WAS 연동상태 점검 결과 정상입니다. Status={actual_status} 상태로 '
                    'WebtoB와 WAS 간 커넥션이 정상 유지되고 있습니다.'
                ),
            )

        return self.warn(
            metrics=metrics,
            thresholds=thresholds,
            reasons=(
                f'파싱한 Status={actual_status} 값이 기대 상태 '
                f'{expected_status}와 일치하지 않습니다.'
            ),
            message=(
                'WEB-WAS 연동상태 점검 결과 경고입니다. '
                f'기대 상태는 {expected_status}이지만 현재 Status={actual_status}로 확인되었습니다.'
            ),
        )


CHECK_CLASS = Check
