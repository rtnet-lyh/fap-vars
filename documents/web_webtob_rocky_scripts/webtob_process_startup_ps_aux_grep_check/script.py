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
        'command not found,not found,No such file,'
        'No such file or directory,Permission denied,cannot,'
        'Connection refused,No route to host,timed out,'
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
        if results:
            return results[0]
        return {
            'command': command,
            'rc': 1,
            'stdout': '',
            'stderr': '명령 실행 결과가 비어 있습니다.',
            'timed_out': False,
        }

    def _run_command_with_rc_marker(self, command, timeout=None):
        wrapped_command = f'{command}; echo {self.FAP_RC_MARKER}$?'
        result = self._run_command(wrapped_command, timeout=timeout)
        return result, self._extract_marker_rc(result.get('stdout') or '')

    def _extract_marker_rc(self, text):
        marker_pattern = re.escape(self.FAP_RC_MARKER) + r'(\d+)'
        match = re.search(marker_pattern, str(text or ''))
        if not match:
            return None
        try:
            return int(match.group(1))
        except Exception:
            return None

    def _remove_marker_line(self, text):
        marker_pattern = re.escape(self.FAP_RC_MARKER) + r'\d+'
        lines = []
        for line in str(text or '').splitlines():
            if re.search(marker_pattern, line):
                continue
            lines.append(line)
        return '\n'.join(lines).strip()

    def _load_thresholds(self):
        process_name = self.get_threshold_var(
            'process_name',
            default='webtob',
            value_type='str',
        )
        ps_status = self.get_threshold_var(
            'ps_status',
            default='S',
            value_type='str',
        )
        bad_process_states = self.get_threshold_var(
            'bad_process_states',
            default='Z,D,T',
            value_type='str',
        )
        failure_keywords = self._get_failure_keywords()

        return {
            'process_name': str(process_name or 'webtob').strip() or 'webtob',
            'ps_status': self._split_csv(ps_status),
            'bad_process_states': self._split_csv(bad_process_states),
            'failure_keywords': failure_keywords,
        }

    def _base_metrics(self, command, result, stdout, stderr, command_rc, thresholds):
        return {
            'command': command,
            'command_rc': command_rc,
            'paramiko_rc': result.get('rc'),
            'timed_out': bool(result.get('timed_out', False)),
            'stdout_line_count': self._line_count(stdout),
            'stderr_line_count': self._line_count(stderr),
            'process_name': thresholds.get('process_name'),
            'ps_status': thresholds.get('ps_status'),
            'bad_process_states': thresholds.get('bad_process_states'),
            'process_count': 0,
            'valid_pid_count': 0,
            'abnormal_state_count': 0,
            'first_process_line': '',
            'first_abnormal_line': '',
            'processes': [],
            'abnormal_processes': [],
        }

    def _is_header_line(self, line):
        parts = re.split(r'\s+', str(line or '').strip())
        if len(parts) < 2:
            return False
        return parts[0].upper() == 'USER' and parts[1].upper() == 'PID'

    def _is_self_or_helper_line(self, raw_line, command_text):
        line = str(raw_line or '').strip()
        lower_line = line.lower()
        parts = re.split(r'\s+', line, maxsplit=10)
        command = parts[10].strip() if len(parts) >= 11 else ''
        command_lower = command.lower()
        first_token = command.split()[0] if command.split() else ''
        base_name = first_token.rsplit('/', 1)[-1].lower()

        if base_name in ('grep', 'egrep', 'awk', 'ps'):
            return True
        if 'ps aux | grep' in command_lower:
            return True
        if self.FAP_RC_MARKER.lower() in lower_line:
            return True
        if command_text and command_text.lower() in lower_line:
            return True
        return False

    def _parse_process_line(self, line):
        parts = re.split(r'\s+', str(line or '').strip(), maxsplit=10)
        if len(parts) < 11:
            return None, '필드 수 부족'

        try:
            pid = int(parts[1])
        except Exception:
            return None, 'PID 파싱 실패'

        try:
            cpu_percent = float(parts[2])
        except Exception:
            return None, '%CPU 파싱 실패'

        try:
            mem_percent = float(parts[3])
        except Exception:
            return None, '%MEM 파싱 실패'

        return {
            'user': parts[0],
            'pid': pid,
            'cpu_percent': cpu_percent,
            'mem_percent': mem_percent,
            'vsz': parts[4],
            'rss': parts[5],
            'tty': parts[6],
            'stat': parts[7],
            'start': parts[8],
            'time': parts[9],
            'command': parts[10],
            'raw_line': str(line or '').strip(),
        }, ''

    def _parse_processes(self, stdout, command_text):
        processes = []
        parse_errors = []
        for raw_line in str(stdout or '').splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if self._is_header_line(line):
                continue
            if self._is_self_or_helper_line(line, command_text):
                continue

            parsed, error = self._parse_process_line(line)
            if parsed is None:
                parse_errors.append({'raw_line': line, 'error': error})
                continue
            processes.append(parsed)
        return processes, parse_errors

    def _has_bad_state(self, stat, bad_states):
        stat_text = str(stat or '').strip()
        for state in bad_states or []:
            state_text = str(state or '').strip()
            if state_text and state_text in stat_text:
                return True
        return False

    def _build_fail(self, error, message, result, stdout, stderr, metrics, thresholds, reasons):
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
        process_name = thresholds['process_name']
        grep_pattern = 'USER|PID|' + process_name
        command = f'ps aux | grep -E {self._quote(grep_pattern)} | grep -v grep'

        result, marker_rc = self._run_command_with_rc_marker(
            command,
            timeout=self.DEFAULT_COMMAND_TIMEOUT,
        )
        raw_stdout = result.get('stdout') or ''
        stdout = self._remove_marker_line(raw_stdout)
        stderr = result.get('stderr') or ''
        command_rc = marker_rc if marker_rc is not None else result.get('rc')

        metrics = self._base_metrics(
            command,
            result,
            stdout,
            stderr,
            command_rc,
            thresholds,
        )

        if result.get('timed_out'):
            return self._build_fail(
                '점검 명령 timeout',
                (
                    '프로세스 기동 점검에 실패했습니다. '
                    f'process_name={process_name} 기준 ps aux 명령이 timeout으로 종료되었습니다.'
                ),
                result,
                stdout,
                stderr,
                metrics,
                thresholds,
                '명령 실행 중 timeout이 발생했습니다.',
            )

        if result.get('rc') != 0:
            return self._build_fail(
                '점검 명령 실행 실패',
                (
                    '프로세스 기동 점검에 실패했습니다. '
                    f'process_name={process_name} 기준 ps aux 명령 실행 결과 rc={result.get("rc")}가 반환되었습니다.'
                ),
                result,
                stdout,
                stderr,
                metrics,
                thresholds,
                f'Paramiko 명령 실행 종료코드가 rc={result.get("rc")}입니다.',
            )

        if marker_rc is None:
            return self._build_fail(
                '점검 명령 종료코드 파싱 실패',
                (
                    '프로세스 기동 점검에 실패했습니다. '
                    '명령 내부 종료코드 marker를 파싱하지 못했습니다.'
                ),
                result,
                stdout,
                stderr,
                metrics,
                thresholds,
                '명령 내부 종료코드 marker가 출력에서 확인되지 않았습니다.',
            )

        failure_keyword = self._contains_failure_keyword(stdout, stderr)
        if failure_keyword:
            return self._build_fail(
                '점검 명령 실행 실패',
                (
                    '프로세스 기동 점검에 실패했습니다. '
                    f'출력에서 실패 키워드가 확인되었습니다: {failure_keyword}'
                ),
                result,
                stdout,
                stderr,
                metrics,
                thresholds,
                f'실패 키워드 감지: {failure_keyword}',
            )

        if marker_rc != 0:
            reason = f'ps aux 또는 grep 계열 명령의 내부 종료코드가 rc={marker_rc}입니다.'
            if marker_rc == 1:
                reason = '대상 프로세스가 없거나 grep 결과가 없습니다.'
            return self._build_fail(
                '대상 프로세스 없음 또는 명령 실패',
                (
                    '프로세스 기동 점검에 실패했습니다. '
                    f'process_name={process_name} 기준 대상 프로세스가 없거나 ps aux 출력에서 확인되지 않았습니다.'
                ),
                result,
                stdout,
                stderr,
                metrics,
                thresholds,
                reason,
            )

        if not stdout.strip():
            return self._build_fail(
                '점검 출력 없음',
                (
                    '프로세스 기동 점검에 실패했습니다. '
                    'ps aux 명령은 실행되었으나 출력이 비어 있어 상태를 판단하지 못했습니다.'
                ),
                result,
                stdout,
                stderr,
                metrics,
                thresholds,
                'ps aux 출력이 비어 있습니다.',
            )

        processes, parse_errors = self._parse_processes(stdout, command)
        abnormal_processes = [
            process for process in processes
            if self._has_bad_state(process.get('stat'), thresholds.get('bad_process_states'))
        ]

        metrics.update({
            'process_count': len(processes),
            'valid_pid_count': len([process for process in processes if isinstance(process.get('pid'), int)]),
            'abnormal_state_count': len(abnormal_processes),
            'first_process_line': processes[0]['raw_line'] if processes else '',
            'first_abnormal_line': abnormal_processes[0]['raw_line'] if abnormal_processes else '',
            'processes': processes,
            'abnormal_processes': abnormal_processes,
            'parse_error_count': len(parse_errors),
            'parse_errors': parse_errors,
        })

        if not processes:
            if parse_errors:
                reason = 'ps aux 출력에서 대상 라인은 확인되었으나 유효한 PID를 파싱하지 못했습니다.'
            else:
                reason = '대상 프로세스가 없습니다.'
            return self._build_fail(
                '대상 프로세스 없음 또는 PID 파싱 실패',
                (
                    '프로세스 기동 점검에 실패했습니다. '
                    f'process_name={process_name} 기준 대상 프로세스가 없거나 ps aux 출력에서 유효한 PID를 파싱하지 못했습니다.'
                ),
                result,
                stdout,
                stderr,
                metrics,
                thresholds,
                reason,
            )

        if metrics.get('valid_pid_count', 0) < 1:
            return self._build_fail(
                'PID 파싱 실패',
                (
                    '프로세스 기동 점검에 실패했습니다. '
                    f'process_name={process_name} 기준 유효한 PID를 하나도 파싱하지 못했습니다.'
                ),
                result,
                stdout,
                stderr,
                metrics,
                thresholds,
                '유효한 PID가 없습니다.',
            )

        if abnormal_processes:
            bad_states = ','.join(thresholds.get('bad_process_states') or [])
            found_states = sorted({process.get('stat') for process in abnormal_processes})
            message = (
                '프로세스 기동 점검 결과 경고입니다. '
                f'process_name={process_name} 기준 대상 프로세스 {len(processes)}건 중 '
                f'{len(abnormal_processes)}건에서 비정상 상태 코드 기준({bad_states})에 해당하는 STAT 값이 확인되었습니다: '
                f'{", ".join(found_states)}.'
            )
            return self.warn(
                metrics=metrics,
                thresholds=thresholds,
                reasons='비정상 상태 코드가 확인되었습니다.',
                message=message,
            )

        bad_states = ','.join(thresholds.get('bad_process_states') or [])
        message = (
            '프로세스 기동 점검 결과 정상입니다. '
            f'process_name={process_name} 기준 대상 프로세스 {len(processes)}건이 확인되었고, '
            f'유효한 PID가 있으며 비정상 상태 코드({bad_states})는 발견되지 않았습니다.'
        )
        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='유효한 PID가 있고 비정상 상태 코드가 발견되지 않았습니다.',
            message=message,
        )


CHECK_CLASS = Check
