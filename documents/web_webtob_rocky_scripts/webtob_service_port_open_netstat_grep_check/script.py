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

    DEFAULT_FAILURE_KEYWORDS = (
        'command not found,not found,No such file,No such file or directory,'
        'Permission denied,cannot,Connection refused,No route to host,timed out,'
        'PARAMIKO_CONNECTION_ERROR,PARAMIKO_COMMAND_TIMEOUT'
    )

    def _split_csv(self, value):
        return [token.strip() for token in str(value or '').split(',') if token.strip()]

    def _line_count(self, text):
        return len([line for line in str(text or '').splitlines() if line.strip()])

    def _validate_port(self, value):
        port_text = str(value or '').strip()
        if not re.match(r'^[0-9]+$', port_text):
            raise ValueError('webtob_service_port 값은 숫자만 허용됩니다: %s' % value)
        port_number = int(port_text)
        if port_number < 1 or port_number > 65535:
            raise ValueError('webtob_service_port 값은 1 이상 65535 이하만 허용됩니다: %s' % value)
        return port_text

    def _get_thresholds(self):
        webtob_service_port = self.get_threshold_var(
            'webtob_service_port',
            default='9080',
            value_type='str',
        )
        allow_stats = self.get_threshold_var(
            'allow_stats',
            default='LISTEN',
            value_type='str',
        )
        failure_keywords_text = self.get_threshold_var(
            'failure_keywords',
            default=self.DEFAULT_FAILURE_KEYWORDS,
            value_type='str',
        )
        failure_keywords = self._split_csv(failure_keywords_text)
        if not failure_keywords:
            failure_keywords = self._split_csv(self.DEFAULT_FAILURE_KEYWORDS)

        return {
            'webtob_service_port': str(webtob_service_port or '').strip(),
            'allow_stats': str(allow_stats or 'LISTEN').strip() or 'LISTEN',
            'failure_keywords': failure_keywords,
        }

    def _allowed_states(self, allow_stats):
        states = [token.strip().upper() for token in str(allow_stats or '').split(',') if token.strip()]
        return states or ['LISTEN']

    def _contains_failure_keyword(self, failure_keywords, *texts):
        combined = '\n'.join(str(text or '') for text in texts if text is not None)
        lowered = combined.lower()
        for keyword in failure_keywords:
            if str(keyword or '').strip().lower() in lowered:
                return str(keyword).strip()
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

    def _run_command_with_rc_marker(self, command, timeout=None):
        wrapped_command = '%s; echo %s$?' % (command, self.FAP_RC_MARKER)
        result = self._run_command(wrapped_command, timeout=timeout)
        marker_rc = self._extract_marker_rc(result.get('stdout') or '')
        return result, marker_rc

    def _extract_marker_rc(self, text):
        match = re.search(re.escape(self.FAP_RC_MARKER) + r'(\d+)', str(text or ''))
        if not match:
            return None
        try:
            return int(match.group(1))
        except Exception:
            return None

    def _remove_marker_lines(self, text):
        marker_re = re.compile(re.escape(self.FAP_RC_MARKER) + r'\d+')
        lines = []
        for line in str(text or '').splitlines():
            if marker_re.search(line):
                continue
            lines.append(line)
        return '\n'.join(lines).strip()

    def _is_header_line(self, line):
        stripped = str(line or '').strip().lower()
        if not stripped:
            return True
        if stripped.startswith('active '):
            return True
        if stripped.startswith('proto '):
            return True
        return False

    def _extract_local_port(self, local_address):
        text = str(local_address or '').strip()
        match = re.search(r'[:.]([0-9]+)$', text)
        if not match:
            return ''
        return match.group(1)

    def _parse_netstat_line(self, line):
        raw_line = str(line or '').rstrip()
        fields = re.split(r'\s+', raw_line.strip())
        if len(fields) < 5:
            return None

        proto = fields[0]
        recv_q = fields[1]
        send_q = fields[2]
        local_address = fields[3]
        foreign_address = fields[4]
        proto_lower = proto.lower()
        state = ''
        if len(fields) >= 6:
            state = fields[-1]
        if proto_lower.startswith('udp') and len(fields) == 5:
            state = ''

        local_port = self._extract_local_port(local_address)
        return {
            'proto': proto,
            'recv_q': recv_q,
            'send_q': send_q,
            'local_address': local_address,
            'foreign_address': foreign_address,
            'state': state,
            'local_port': local_port,
            'raw_line': raw_line,
        }

    def _parse_entries(self, stdout, target_port):
        matched_lines = []
        entries = []
        unparsable_lines = []

        for line in str(stdout or '').splitlines():
            raw_line = str(line or '').rstrip()
            if self._is_header_line(raw_line):
                continue
            matched_lines.append(raw_line)
            entry = self._parse_netstat_line(raw_line)
            if not entry:
                unparsable_lines.append(raw_line)
                continue
            if entry.get('local_port') != target_port:
                continue
            entries.append(entry)

        return matched_lines, entries, unparsable_lines

    def _build_metrics(self, command='', result=None, stdout='', stderr='', marker_rc=None,
                       port='', allow_stats='', matched_lines=None, entries=None):
        result = result or {}
        matched_lines = matched_lines or []
        entries = entries or []
        allowed_states = self._allowed_states(allow_stats)

        tcp_entries = [entry for entry in entries if str(entry.get('proto') or '').lower() in ('tcp', 'tcp6')]
        non_tcp_entries = [entry for entry in entries if str(entry.get('proto') or '').lower() not in ('tcp', 'tcp6')]
        listening_entries = [entry for entry in tcp_entries if str(entry.get('state') or '').upper() in allowed_states]
        non_listen_entries = [entry for entry in tcp_entries if str(entry.get('state') or '').upper() not in allowed_states]

        first_abnormal_line = ''
        if non_tcp_entries:
            first_abnormal_line = non_tcp_entries[0].get('raw_line') or ''
        elif non_listen_entries:
            first_abnormal_line = non_listen_entries[0].get('raw_line') or ''

        valid_port_line_count = len(entries)
        protocol_ok = valid_port_line_count > 0 and len(non_tcp_entries) == 0
        state_ok = valid_port_line_count > 0 and len(tcp_entries) > 0 and len(non_listen_entries) == 0 and len(non_tcp_entries) == 0
        port_open = valid_port_line_count > 0

        return {
            'command': command,
            'command_rc': result.get('rc'),
            'timed_out': bool(result.get('timed_out', False)),
            'stdout_line_count': self._line_count(stdout),
            'stderr_line_count': self._line_count(stderr),
            'webtob_service_port': port,
            'allow_stats': allow_stats,
            'marker_rc': marker_rc,
            'matched_line_count': len(matched_lines),
            'valid_port_line_count': valid_port_line_count,
            'listening_line_count': len(listening_entries),
            'non_tcp_line_count': len(non_tcp_entries),
            'non_listen_line_count': len(non_listen_entries),
            'first_matched_line': matched_lines[0] if matched_lines else '',
            'first_valid_port_line': entries[0].get('raw_line') if entries else '',
            'first_abnormal_line': first_abnormal_line,
            'port_open': port_open,
            'protocol_ok': protocol_ok,
            'state_ok': state_ok,
            'entries': entries,
        }

    def _failure(self, title, message, stdout, stderr, metrics, thresholds, reasons):
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
        thresholds = self._get_thresholds()
        port_value = thresholds.get('webtob_service_port')
        allow_stats = thresholds.get('allow_stats')
        failure_keywords = thresholds.get('failure_keywords') or []

        command = ''
        try:
            port = self._validate_port(port_value)
        except ValueError as exc:
            metrics = self._build_metrics(
                command=command,
                result={},
                stdout='',
                stderr='',
                marker_rc=None,
                port=str(port_value or '').strip(),
                allow_stats=allow_stats,
                matched_lines=[],
                entries=[],
            )
            return self._failure(
                '임계치 오류',
                '서비스 포트 오픈 상태 점검에 실패했습니다. webtob_service_port 값 오류로 포트 오픈 상태를 판단하지 못했습니다.',
                '',
                '',
                metrics,
                thresholds,
                str(exc),
            )

        port_pattern = '(^|[^0-9])%s([^0-9]|$)' % port
        inner_command = "netstat -an | grep -E %s" % shlex.quote(port_pattern)
        command = 'bash -o pipefail -c %s' % shlex.quote(inner_command)

        result, marker_rc = self._run_command_with_rc_marker(command, timeout=self.DEFAULT_COMMAND_TIMEOUT)
        raw_stdout = result.get('stdout') or ''
        stderr = result.get('stderr') or ''
        stdout = self._remove_marker_lines(raw_stdout)

        matched_lines, entries, unparsable_lines = self._parse_entries(stdout, port)
        metrics = self._build_metrics(
            command=command,
            result=result,
            stdout=stdout,
            stderr=stderr,
            marker_rc=marker_rc,
            port=port,
            allow_stats=allow_stats,
            matched_lines=matched_lines,
            entries=entries,
        )

        if result.get('timed_out'):
            return self._failure(
                '점검 명령 timeout',
                '서비스 포트 오픈 상태 점검에 실패했습니다. netstat 명령 실행 중 timeout이 발생해 포트 오픈 상태를 판단하지 못했습니다.',
                raw_stdout,
                stderr,
                metrics,
                thresholds,
                '명령 실행 timeout',
            )

        failure_keyword = self._contains_failure_keyword(failure_keywords, raw_stdout, stderr)
        if failure_keyword:
            return self._failure(
                '점검 명령 실행 실패',
                '서비스 포트 오픈 상태 점검에 실패했습니다. netstat 명령 실행 오류 또는 권한 문제로 포트 오픈 상태를 판단하지 못했습니다.',
                raw_stdout,
                stderr,
                metrics,
                thresholds,
                '실패 키워드 감지: %s' % failure_keyword,
            )

        if marker_rc is None:
            return self._failure(
                '점검 명령 실행 실패',
                '서비스 포트 오픈 상태 점검에 실패했습니다. 명령 내부 종료코드 marker를 확인하지 못해 포트 오픈 상태를 판단하지 못했습니다.',
                raw_stdout,
                stderr,
                metrics,
                thresholds,
                'marker rc 확인 실패',
            )

        if marker_rc == 1:
            return self._failure(
                '서비스 포트 미오픈',
                '서비스 포트 오픈 상태 점검에 실패했습니다. webtob_service_port=%s 기준 netstat 출력이 없거나 대상 포트 라인이 확인되지 않았습니다.' % port,
                raw_stdout,
                stderr,
                metrics,
                thresholds,
                '대상 포트 출력 없음',
            )

        if marker_rc >= 2:
            return self._failure(
                '점검 명령 실행 실패',
                '서비스 포트 오픈 상태 점검에 실패했습니다. netstat 또는 grep 명령 실행 오류로 포트 오픈 상태를 판단하지 못했습니다.',
                raw_stdout,
                stderr,
                metrics,
                thresholds,
                '명령 내부 종료코드 오류: marker_rc=%s' % marker_rc,
            )

        if result.get('rc') != 0 and not entries:
            return self._failure(
                '점검 명령 실행 실패',
                '서비스 포트 오픈 상태 점검에 실패했습니다. 원격 명령 실행 오류로 포트 오픈 상태를 판단하지 못했습니다.',
                raw_stdout,
                stderr,
                metrics,
                thresholds,
                '원격 명령 종료코드 오류: rc=%s' % result.get('rc'),
            )

        if not stdout.strip():
            return self._failure(
                '점검 출력 없음',
                '서비스 포트 오픈 상태 점검에 실패했습니다. netstat 명령 출력이 비어 있어 포트 오픈 상태를 판단하지 못했습니다.',
                raw_stdout,
                stderr,
                metrics,
                thresholds,
                '출력 없음',
            )

        if not entries:
            reason = '대상 포트 파싱 실패'
            if unparsable_lines:
                reason = 'netstat 출력 파싱 실패'
            return self._failure(
                '대상 포트 파싱 실패',
                '서비스 포트 오픈 상태 점검에 실패했습니다. netstat 출력에서 webtob_service_port=%s 로컬 포트 라인을 파싱하지 못했습니다.' % port,
                raw_stdout,
                stderr,
                metrics,
                thresholds,
                reason,
            )

        if metrics.get('protocol_ok') and metrics.get('state_ok') and metrics.get('listening_line_count', 0) > 0:
            return self.ok(
                metrics=metrics,
                thresholds=thresholds,
                reasons='대상 포트가 tcp/tcp6 프로토콜이며 허용 상태(%s)와 일치합니다.' % allow_stats,
                message=(
                    '서비스 포트 오픈 상태 점검 결과 정상입니다. '
                    'webtob_service_port=%s 기준 netstat 출력에서 tcp/tcp6 %s 상태의 포트 라인이 확인되었습니다.'
                    % (port, allow_stats)
                ),
            )

        return self.warn(
            metrics=metrics,
            thresholds=thresholds,
            reasons='대상 포트 라인은 존재하지만 프로토콜 또는 상태가 허용 기준과 일치하지 않습니다.',
            message=(
                '서비스 포트 오픈 상태 점검 결과 경고입니다. '
                'webtob_service_port=%s 기준 포트 라인은 확인되었으나 프로토콜이 tcp/tcp6가 아니거나 상태가 %s이 아닙니다.'
                % (port, allow_stats)
            ),
        )


CHECK_CLASS = Check
