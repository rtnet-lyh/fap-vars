# -*- coding: utf-8 -*-

import re
import shlex

from .common._base import BaseCheck


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'linux'
    PARAMIKO_REUSE_SESSION = False

    DEFAULT_COMMAND_TIMEOUT = 5
    DEFAULT_IP_ADDR = '127.0.0.1'
    DEFAULT_SERVICE_PORT = '9080'
    DEFAULT_REQUIRED_CONNECTION_MESSAGE = 'Connected to'
    DEFAULT_FAILURE_KEYWORDS = (
        'command not found,not found,No such file,No such file or directory,'
        'Permission denied,cannot,Connection refused,No route to host,timed out,'
        'PARAMIKO_CONNECTION_ERROR,PARAMIKO_COMMAND_TIMEOUT'
    )

    CONNECTION_FAILURE_MARKERS = (
        'Connection refused',
        'No route to host',
        'Network is unreachable',
        'Connection timed out',
        'Unable to connect',
        'Name or service not known',
        'Temporary failure in name resolution',
        'could not resolve',
        'telnet:',
    )

    EXECUTION_FAILURE_MARKERS = (
        'command not found',
        'not found',
        'No such file',
        'No such file or directory',
        'Permission denied',
        'cannot',
        'PARAMIKO_CONNECTION_ERROR',
        'PARAMIKO_COMMAND_TIMEOUT',
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

    def _validate_port(self, value, key='webtob_service_port'):
        port_text = str(value or '').strip()
        if not re.match(r'^[0-9]{1,5}$', port_text):
            raise ValueError('%s 값이 올바르지 않습니다: %s' % (key, value))

        port_number = int(port_text)
        if port_number < 1 or port_number > 65535:
            raise ValueError('%s 값이 허용 범위를 벗어났습니다: %s' % (key, value))

        return port_text

    def _get_failure_keywords(self):
        raw_keywords = self.get_threshold_var(
            'failure_keywords',
            default=self.DEFAULT_FAILURE_KEYWORDS,
            value_type='str',
        )
        return self._split_csv(raw_keywords)

    def _load_thresholds(self):
        ip_addr = self.get_threshold_var(
            'ip_addr',
            default=self.DEFAULT_IP_ADDR,
            value_type='str',
        )
        ip_addr = str(ip_addr or '').strip() or self.DEFAULT_IP_ADDR

        webtob_service_port = self.get_threshold_var(
            'webtob_service_port',
            default=self.DEFAULT_SERVICE_PORT,
            value_type='str',
        )

        required_connection_message = self.get_threshold_var(
            'required_connection_message',
            default=self.DEFAULT_REQUIRED_CONNECTION_MESSAGE,
            value_type='str',
        )
        required_connection_message = (
            str(required_connection_message or '').strip()
            or self.DEFAULT_REQUIRED_CONNECTION_MESSAGE
        )

        return {
            'ip_addr': ip_addr,
            'webtob_service_port': webtob_service_port,
            'required_connection_message': required_connection_message,
            'failure_keywords': self._get_failure_keywords(),
        }

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
                'raw_output': '',
                'timed_out': False,
            }
        return results[0]

    def _lines(self, *texts):
        lines = []
        for text in texts:
            for line in str(text or '').splitlines():
                stripped = line.strip()
                if stripped:
                    lines.append(stripped)
        return lines

    def _first_output_line(self, *texts):
        lines = self._lines(*texts)
        return lines[0] if lines else ''

    def _find_case_insensitive_line(self, markers, *texts):
        normalized_markers = [str(marker or '').strip() for marker in markers if str(marker or '').strip()]
        if not normalized_markers:
            return '', ''

        for line in self._lines(*texts):
            line_lower = line.lower()
            for marker in normalized_markers:
                if marker.lower() in line_lower:
                    return line, marker
        return '', ''

    def _success_markers(self, ip_addr, required_connection_message):
        markers = ['Connected to']
        ip_text = str(ip_addr or '').strip()
        if ip_text:
            markers.append('Connected to %s' % ip_text)
            markers.append('Connected to %s.' % ip_text)

        required = str(required_connection_message or '').strip()
        if required:
            markers.append(required)
            if '[목적지 IP]' in required:
                markers.append(required.replace('[목적지 IP]', ip_text))
            if '{{ destination_ip }}' in required:
                markers.append(required.replace('{{ destination_ip }}', ip_text))
            if '<ip_addr>' in required:
                markers.append(required.replace('<ip_addr>', ip_text))

        deduped = []
        seen = set()
        for marker in markers:
            key = marker.lower()
            if key not in seen:
                seen.add(key)
                deduped.append(marker)
        return deduped

    def _find_execution_failure(self, failure_keywords, *texts):
        combined = '\n'.join(str(text or '') for text in texts if text is not None)
        combined_lower = combined.lower()
        if not combined_lower:
            return '', ''

        connection_keys = set(marker.lower() for marker in self.CONNECTION_FAILURE_MARKERS)
        execution_markers = list(self.EXECUTION_FAILURE_MARKERS)
        for keyword in failure_keywords:
            text = str(keyword or '').strip()
            if not text:
                continue
            if text.lower() in connection_keys or text.lower() == 'timed out':
                continue
            if text not in execution_markers:
                execution_markers.append(text)

        for marker in execution_markers:
            marker_text = str(marker or '').strip()
            if marker_text and marker_text.lower() in combined_lower:
                line, _ = self._find_case_insensitive_line([marker_text], *texts)
                return line, marker_text
        return '', ''

    def _build_metrics(
        self,
        command,
        result,
        stdout,
        stderr,
        ip_addr,
        webtob_service_port,
        required_connection_message,
        connected=False,
        connection_message_found=False,
        failure_message='',
        first_output_line='',
        matched_success_line='',
        matched_failure_line='',
    ):
        return {
            'command': command,
            'command_rc': result.get('rc'),
            'timed_out': bool(result.get('timed_out', False)),
            'stdout_line_count': self._line_count(stdout),
            'stderr_line_count': self._line_count(stderr),
            'ip_addr': ip_addr,
            'webtob_service_port': webtob_service_port,
            'required_connection_message': required_connection_message,
            'connected': bool(connected),
            'connection_message_found': bool(connection_message_found),
            'failure_message': failure_message or '',
            'first_output_line': first_output_line or '',
            'matched_success_line': matched_success_line or '',
            'matched_failure_line': matched_failure_line or '',
        }

    def _fail_result(self, error, message, stdout, stderr, metrics, thresholds, reasons):
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
        ip_addr = thresholds['ip_addr']
        required_connection_message = thresholds['required_connection_message']

        command = ''
        empty_result = {
            'command': command,
            'rc': None,
            'stdout': '',
            'stderr': '',
            'raw_output': '',
            'timed_out': False,
        }

        try:
            port_text = self._validate_port(thresholds['webtob_service_port'])
        except ValueError as exc:
            webtob_service_port = str(thresholds.get('webtob_service_port') or '').strip()
            metrics = self._build_metrics(
                command,
                empty_result,
                '',
                '',
                ip_addr,
                webtob_service_port,
                required_connection_message,
                failure_message=str(exc),
            )
            return self._fail_result(
                '포트 임계치 오류',
                '서비스 포트 접속 정상 확인에 실패했습니다. webtob_service_port 값 오류로 상태를 판단하지 못했습니다.',
                '',
                '',
                metrics,
                thresholds,
                str(exc),
            )

        thresholds['webtob_service_port'] = port_text
        command = 'echo quit | telnet %s %s' % (self._quote(ip_addr), port_text)
        result = self._run_command(command, timeout=self.DEFAULT_COMMAND_TIMEOUT)

        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()
        raw_output = (result.get('raw_output') or '').strip()
        first_output_line = self._first_output_line(stdout, stderr, raw_output)

        success_markers = self._success_markers(ip_addr, required_connection_message)
        matched_success_line, _ = self._find_case_insensitive_line(
            success_markers,
            stdout,
            stderr,
            raw_output,
        )
        matched_failure_line, failure_marker = self._find_case_insensitive_line(
            self.CONNECTION_FAILURE_MARKERS,
            stdout,
            stderr,
            raw_output,
        )
        execution_failure_line, execution_failure_marker = self._find_execution_failure(
            thresholds.get('failure_keywords') or [],
            stdout,
            stderr,
            raw_output,
        )

        connected = bool(matched_success_line)
        connection_message_found = connected
        failure_message = execution_failure_marker or failure_marker or ''

        metrics = self._build_metrics(
            command,
            result,
            stdout,
            stderr,
            ip_addr,
            port_text,
            required_connection_message,
            connected=connected,
            connection_message_found=connection_message_found,
            failure_message=failure_message,
            first_output_line=first_output_line,
            matched_success_line=matched_success_line,
            matched_failure_line=execution_failure_line or matched_failure_line,
        )

        if result.get('timed_out'):
            metrics['failure_message'] = 'PARAMIKO_COMMAND_TIMEOUT'
            return self._fail_result(
                '점검 명령 timeout',
                '서비스 포트 접속 정상 확인에 실패했습니다. telnet 명령 실행 중 timeout이 발생하여 상태를 판단하지 못했습니다.',
                stdout,
                stderr,
                metrics,
                thresholds,
                '명령 실행 중 timeout이 발생했습니다.',
            )

        if execution_failure_marker:
            metrics['failure_message'] = execution_failure_marker
            metrics['matched_failure_line'] = execution_failure_line
            return self._fail_result(
                'telnet 명령 실행 오류',
                '서비스 포트 접속 정상 확인에 실패했습니다. telnet 명령 실행 오류 또는 권한 문제로 상태를 판단하지 못했습니다.',
                stdout,
                stderr,
                metrics,
                thresholds,
                '출력에서 명령 실행 실패 키워드가 확인되었습니다: %s' % execution_failure_marker,
            )

        if not first_output_line:
            metrics['failure_message'] = '출력 없음'
            return self._fail_result(
                '점검 출력 없음',
                '서비스 포트 접속 정상 확인에 실패했습니다. telnet 명령 실행 결과가 비어 있어 상태를 판단하지 못했습니다.',
                stdout,
                stderr,
                metrics,
                thresholds,
                '명령 출력이 없습니다.',
            )

        if failure_marker:
            metrics['failure_message'] = failure_marker
            metrics['matched_failure_line'] = matched_failure_line
            message = (
                '서비스 포트 접속 정상 확인 결과 경고입니다. '
                '%s:%s 대상으로 telnet 접속을 시도했으나 %s 문구가 확인되어 서비스 포트 접속이 실패했습니다.'
                % (ip_addr, port_text, failure_marker)
            )
            return self.warn(
                metrics=metrics,
                thresholds=thresholds,
                reasons='서비스 포트 접속 실패 문구가 확인되었습니다: %s' % failure_marker,
                message=message,
            )

        if connected:
            message = (
                '서비스 포트 접속 정상 확인 결과 정상입니다. '
                '%s:%s 대상으로 telnet 접속 시 %s 문구가 확인되어 서비스 포트 통신이 가능합니다.'
                % (ip_addr, port_text, required_connection_message)
            )
            return self.ok(
                metrics=metrics,
                thresholds=thresholds,
                reasons='telnet 연결 성공 문구가 확인되었습니다.',
                message=message,
            )

        rc = result.get('rc')
        if rc not in (0, None):
            metrics['failure_message'] = '비정상 종료코드 rc=%s' % rc
            return self._fail_result(
                '점검 명령 실행 실패',
                '서비스 포트 접속 정상 확인에 실패했습니다. telnet 명령 종료코드가 비정상이고 연결 성공 문구가 없어 상태를 판단하지 못했습니다.',
                stdout,
                stderr,
                metrics,
                thresholds,
                '명령 종료코드가 rc=%s입니다.' % rc,
            )

        metrics['failure_message'] = '접속 결과 파싱 실패'
        return self._fail_result(
            '접속 결과 파싱 실패',
            '서비스 포트 접속 정상 확인에 실패했습니다. telnet 출력에서 연결 성공 또는 연결 실패 문구를 확인하지 못해 상태를 판단하지 못했습니다.',
            stdout,
            stderr,
            metrics,
            thresholds,
            'telnet 출력에서 판단 기준 문구가 확인되지 않았습니다.',
        )


CHECK_CLASS = Check
