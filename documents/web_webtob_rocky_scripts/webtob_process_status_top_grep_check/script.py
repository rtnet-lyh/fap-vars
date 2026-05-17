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

    def _load_thresholds(self):
        process_name = self.get_threshold_var(
            'process_name',
            default='wsm|htl|hth',
            value_type='str',
        )
        ps_status = self.get_threshold_var(
            'ps_status',
            default='S',
            value_type='str',
        )
        bad_process_states = self.get_threshold_var(
            'bad_process_states',
            default='Z,T,D',
            value_type='str',
        )
        failure_keywords_text = self.get_threshold_var(
            'failure_keywords',
            default=(
                'command not found,not found,No such file,'
                'No such file or directory,Permission denied,cannot,'
                'Connection refused,No route to host,timed out,'
                'PARAMIKO_CONNECTION_ERROR,PARAMIKO_COMMAND_TIMEOUT'
            ),
            value_type='str',
        )
        failure_keywords = self._split_csv(failure_keywords_text)
        bad_states = self._split_csv(bad_process_states)
        expected_states = self._split_csv(ps_status)

        return {
            'process_name': str(process_name or '').strip() or 'wsm|htl|hth',
            'ps_status': str(ps_status or '').strip() or 'S',
            'bad_process_states': str(bad_process_states or '').strip() or 'Z,T,D',
            'bad_process_state_list': bad_states or ['Z', 'T', 'D'],
            'ps_status_list': expected_states or ['S'],
            'failure_keywords': failure_keywords,
            'failure_keywords_text': failure_keywords_text,
        }

    def _contains_failure_keyword(self, *texts):
        failure_keywords = self._load_thresholds().get('failure_keywords') or []
        combined = '\n'.join(str(text or '') for text in texts if text is not None)
        combined_lower = combined.lower()
        for keyword in failure_keywords:
            keyword_text = str(keyword or '').strip()
            if keyword_text and keyword_text.lower() in combined_lower:
                return keyword_text
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
                'display_command': command,
                'rc': 1,
                'stdout': '',
                'stderr': '명령 실행 결과가 비어 있습니다.',
                'timed_out': False,
                'raw_output': '',
            }
        return results[0]

    def _base_metrics(self, result, stdout, stderr, command, thresholds):
        return {
            'command': command,
            'command_rc': result.get('rc'),
            'timed_out': bool(result.get('timed_out', False)),
            'stdout_line_count': self._line_count(stdout),
            'stderr_line_count': self._line_count(stderr),
            'process_name': thresholds.get('process_name'),
            'ps_status': thresholds.get('ps_status'),
            'bad_process_states': thresholds.get('bad_process_state_list'),
            'process_count': 0,
            'valid_pid_count': 0,
            'abnormal_state_count': 0,
            'top_header_line': '',
            'first_process_line': '',
            'first_abnormal_line': '',
            'processes': [],
            'abnormal_processes': [],
        }

    def _result_thresholds(self, thresholds):
        return {
            'process_name': thresholds.get('process_name'),
            'ps_status': thresholds.get('ps_status'),
            'bad_process_states': thresholds.get('bad_process_states'),
            'failure_keywords': thresholds.get('failure_keywords'),
        }

    def _find_top_header(self, stdout):
        lines = [line.rstrip() for line in str(stdout or '').splitlines() if line.strip()]
        for index, line in enumerate(lines):
            tokens = re.split(r'\s+', line.strip())
            normalized = [token.upper() for token in tokens]
            if 'PID' in normalized and 'COMMAND' in normalized and 'S' in normalized:
                return index, line, tokens, lines
        return -1, '', [], lines

    def _required_column_indexes(self, header_tokens):
        normalized = [token.upper() for token in header_tokens]
        indexes = {}
        for name in ('PID', 'USER', 'PR', 'NI', 'VIRT', 'RES', 'SHR', 'S', '%CPU', '%MEM', 'COMMAND'):
            if name not in normalized:
                return None
            indexes[name] = normalized.index(name)

        time_index = None
        for idx, token in enumerate(normalized):
            if token.startswith('TIME'):
                time_index = idx
                break
        if time_index is None:
            return None
        indexes['TIME'] = time_index
        return indexes

    def _is_self_command_line(self, line, command_name):
        raw_lower = str(line or '').lower()
        command_lower = str(command_name or '').strip().lower()
        command_base = command_lower.split()[0] if command_lower else ''
        self_command_names = ('grep', 'egrep', 'top')
        if command_base in self_command_names:
            return True
        if 'grep -e' in raw_lower or 'egrep ' in raw_lower:
            return True
        if 'top -b -n 1' in raw_lower:
            return True
        return False

    def _parse_float(self, value):
        return float(str(value).strip().replace(',', '.'))

    def _parse_process_line(self, line, header_tokens, indexes, process_pattern):
        command_index = indexes.get('COMMAND')
        parts = re.split(r'\s+', line.strip(), maxsplit=command_index)
        if len(parts) <= command_index:
            return None, 'top 프로세스 라인의 컬럼 수가 부족합니다: ' + line

        def token(column):
            idx = indexes.get(column)
            if idx is None or idx >= len(parts):
                raise ValueError('컬럼 누락: ' + column)
            return parts[idx]

        try:
            pid = int(token('PID'))
        except Exception:
            return None, '유효한 PID를 파싱하지 못했습니다: ' + line

        try:
            cpu_percent = self._parse_float(token('%CPU'))
            memory_percent = self._parse_float(token('%MEM'))
        except Exception:
            return None, 'CPU 또는 메모리 사용률을 파싱하지 못했습니다: ' + line

        try:
            command_name = token('COMMAND')
            state = token('S')
            process = {
                'pid': pid,
                'user': token('USER'),
                'pr': token('PR'),
                'ni': token('NI'),
                'virt': token('VIRT'),
                'res': token('RES'),
                'shr': token('SHR'),
                'state': state,
                'cpu_percent': cpu_percent,
                'memory_percent': memory_percent,
                'time': token('TIME'),
                'command_name': command_name,
                'raw_line': line,
            }
        except Exception as exc:
            return None, 'top 프로세스 라인을 파싱하지 못했습니다: {0}: {1}'.format(str(exc), line)

        if self._is_self_command_line(line, command_name):
            return None, ''

        try:
            if not process_pattern.search(line):
                return None, ''
        except Exception as exc:
            return None, 'process_name 정규식 매칭 중 오류가 발생했습니다: ' + str(exc)

        return process, ''

    def _has_bad_state(self, state, bad_states):
        state_text = str(state or '').upper()
        for bad_state in bad_states:
            bad_text = str(bad_state or '').strip().upper()
            if bad_text and bad_text in state_text:
                return True
        return False

    def run(self):
        thresholds = self._load_thresholds()
        process_name = thresholds.get('process_name')
        bad_states = thresholds.get('bad_process_state_list') or ['Z', 'T', 'D']
        command = 'top -b -n 1 | grep -E {0}'.format(self._quote('PID|' + process_name))
        result = self._run_command(command, timeout=self.DEFAULT_COMMAND_TIMEOUT)

        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()
        metrics = self._base_metrics(result, stdout, stderr, command, thresholds)
        result_thresholds = self._result_thresholds(thresholds)

        if result.get('timed_out'):
            message = '프로세스 사용 상태 점검에 실패했습니다. top 명령 실행이 timeout 되어 프로세스 상태를 판단하지 못했습니다.'
            return self.fail(
                '점검 명령 timeout',
                message=message,
                stdout=stdout,
                stderr=stderr,
                metrics=metrics,
                thresholds=result_thresholds,
                reasons='top -b -n 1 명령 실행 중 timeout 발생',
            )

        rc = result.get('rc')
        if rc != 0:
            if not stdout:
                reason = '대상 프로세스가 없거나 grep 결과가 없습니다.'
            else:
                reason = '명령 종료코드가 rc={0}입니다.'.format(rc)
            message = '프로세스 사용 상태 점검에 실패했습니다. {0}'.format(reason)
            return self.fail(
                '점검 명령 실행 실패',
                message=message,
                stdout=stdout,
                stderr=stderr,
                metrics=metrics,
                thresholds=result_thresholds,
                reasons=reason,
            )

        failure_keyword = self._contains_failure_keyword(stdout, stderr)
        if failure_keyword:
            message = '프로세스 사용 상태 점검에 실패했습니다. 출력에서 실패 키워드가 확인되었습니다: {0}'.format(failure_keyword)
            return self.fail(
                '점검 명령 실행 실패',
                message=message,
                stdout=stdout,
                stderr=stderr,
                metrics=metrics,
                thresholds=result_thresholds,
                reasons='실패 키워드 확인: ' + failure_keyword,
            )

        if not stdout:
            message = '프로세스 사용 상태 점검에 실패했습니다. 대상 프로세스가 없거나 top 출력이 비어 있어 프로세스 상태를 판단하지 못했습니다.'
            return self.fail(
                '점검 출력 없음',
                message=message,
                stdout=stdout,
                stderr=stderr,
                metrics=metrics,
                thresholds=result_thresholds,
                reasons='stdout 출력 없음',
            )

        header_index, header_line, header_tokens, lines = self._find_top_header(stdout)
        metrics['top_header_line'] = header_line
        if header_index < 0:
            message = '프로세스 사용 상태 점검에 실패했습니다. top 출력에서 PID/COMMAND/S 헤더를 찾지 못해 프로세스 상태를 판단하지 못했습니다.'
            return self.fail(
                'top 헤더 파싱 실패',
                message=message,
                stdout=stdout,
                stderr=stderr,
                metrics=metrics,
                thresholds=result_thresholds,
                reasons='top 헤더 라인 미검출',
            )

        indexes = self._required_column_indexes(header_tokens)
        if indexes is None:
            message = '프로세스 사용 상태 점검에 실패했습니다. top 헤더에서 상태 컬럼 S, COMMAND, %CPU, %MEM 컬럼을 파싱하지 못했습니다.'
            return self.fail(
                'top 컬럼 파싱 실패',
                message=message,
                stdout=stdout,
                stderr=stderr,
                metrics=metrics,
                thresholds=result_thresholds,
                reasons='필수 top 컬럼 미검출',
            )

        try:
            process_pattern = re.compile(process_name)
        except Exception as exc:
            message = '프로세스 사용 상태 점검에 실패했습니다. process_name 정규식이 올바르지 않습니다: {0}'.format(str(exc))
            return self.fail(
                '임계치 오류',
                message=message,
                stdout=stdout,
                stderr=stderr,
                metrics=metrics,
                thresholds=result_thresholds,
                reasons='process_name 정규식 오류',
            )

        processes = []
        parse_errors = []
        for line in lines[header_index + 1:]:
            if not line.strip():
                continue
            process, parse_error = self._parse_process_line(line, header_tokens, indexes, process_pattern)
            if parse_error:
                parse_errors.append(parse_error)
                continue
            if process:
                processes.append(process)

        metrics['processes'] = processes
        metrics['process_count'] = len(processes)
        metrics['valid_pid_count'] = len([process for process in processes if isinstance(process.get('pid'), int)])
        metrics['first_process_line'] = processes[0].get('raw_line') if processes else ''

        if parse_errors:
            message = '프로세스 사용 상태 점검에 실패했습니다. top 프로세스 라인 파싱 중 오류가 발생해 프로세스 상태를 판단하지 못했습니다.'
            return self.fail(
                'top 프로세스 파싱 실패',
                message=message,
                stdout=stdout,
                stderr=stderr,
                metrics=metrics,
                thresholds=result_thresholds,
                reasons='; '.join(parse_errors[:3]),
            )

        if not processes:
            message = '프로세스 사용 상태 점검에 실패했습니다. process_name={0} 기준 대상 프로세스가 없거나 top 출력에서 대상 프로세스를 찾지 못했습니다.'.format(process_name)
            return self.fail(
                '대상 프로세스 없음',
                message=message,
                stdout=stdout,
                stderr=stderr,
                metrics=metrics,
                thresholds=result_thresholds,
                reasons='대상 프로세스 미검출',
            )

        abnormal_processes = [
            process for process in processes
            if self._has_bad_state(process.get('state'), bad_states)
        ]
        metrics['abnormal_processes'] = abnormal_processes
        metrics['abnormal_state_count'] = len(abnormal_processes)
        metrics['first_abnormal_line'] = abnormal_processes[0].get('raw_line') if abnormal_processes else ''

        if abnormal_processes:
            states = sorted(set(str(process.get('state') or '') for process in abnormal_processes))
            message = (
                '프로세스 사용 상태 점검 결과 경고입니다. '
                'process_name={0} 기준 대상 프로세스 {1}건 중 {2}건에서 비정상 상태 코드 {3}가 확인되었습니다.'
            ).format(
                process_name,
                len(processes),
                len(abnormal_processes),
                ','.join(states),
            )
            return self.warn(
                metrics=metrics,
                thresholds=result_thresholds,
                reasons='비정상 프로세스 상태 확인: ' + ','.join(states),
                message=message,
            )

        message = (
            '프로세스 사용 상태 점검 결과 정상입니다. '
            'process_name={0} 기준 대상 프로세스 {1}건이 확인되었고, 비정상 상태 코드({2})는 발견되지 않았습니다.'
        ).format(process_name, len(processes), ','.join(bad_states))
        return self.ok(
            metrics=metrics,
            thresholds=result_thresholds,
            reasons='대상 프로세스 상태에 비정상 상태 코드가 없습니다.',
            message=message,
        )


CHECK_CLASS = Check
