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

    def _load_thresholds(self):
        process_name = self.get_threshold_var(
            'process_name',
            default='wsm|htl|hth',
            value_type='str',
        )
        max_cpu_usage_percent = self.get_threshold_var(
            'max_cpu_usage_percent',
            default=70,
            value_type='float',
        )
        failure_keywords = self._get_failure_keywords()

        process_name = str(process_name or '').strip()
        if not process_name:
            process_name = 'wsm|htl|hth'

        return {
            'process_name': process_name,
            'max_cpu_usage_percent': float(max_cpu_usage_percent),
            'failure_keywords': failure_keywords,
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
                'display_command': command,
                'rc': 1,
                'stdout': '',
                'stderr': '명령 실행 결과가 비어 있습니다.',
                'timed_out': False,
            }
        return results[0]

    def _base_metrics(self, command, result, stdout, stderr, thresholds):
        return {
            'command': command,
            'command_rc': result.get('rc'),
            'timed_out': bool(result.get('timed_out', False)),
            'stdout_line_count': self._line_count(stdout),
            'stderr_line_count': self._line_count(stderr),
            'process_name': thresholds.get('process_name'),
            'max_cpu_usage_percent': thresholds.get('max_cpu_usage_percent'),
            'process_count': 0,
            'max_observed_cpu_percent': None,
            'over_threshold_count': 0,
            'top_header_line': '',
            'first_process_line': '',
            'highest_cpu_process_line': '',
            'over_threshold_lines': [],
            'processes': [],
        }

    def _fail(self, error, message, result, metrics, thresholds, stdout, stderr, reasons):
        return self.fail(
            error,
            message=message,
            stdout=(stdout or '').strip(),
            stderr=(stderr or '').strip(),
            metrics=metrics,
            thresholds=thresholds,
            reasons=reasons,
        )

    def _find_top_header(self, lines):
        for index, line in enumerate(lines):
            tokens = re.split(r'\s+', line.strip())
            normalized = [token.upper() for token in tokens]
            if 'PID' in normalized and '%CPU' in normalized and 'COMMAND' in normalized:
                return index, line.strip(), tokens
        return None, '', []

    def _is_self_command_line(self, line):
        lowered = str(line or '').lower()
        self_markers = (
            'grep -e',
            'grep -E'.lower(),
            'egrep',
            'top -b -n 1',
            'sh -c',
            'bash -c',
        )
        return any(marker in lowered for marker in self_markers)

    def _parse_process_line(self, line, header_tokens, process_pattern):
        normalized_header = [token.upper() for token in header_tokens]
        cpu_index = normalized_header.index('%CPU')
        command_index = normalized_header.index('COMMAND')
        pid_index = normalized_header.index('PID') if 'PID' in normalized_header else 0
        user_index = normalized_header.index('USER') if 'USER' in normalized_header else 1
        state_index = normalized_header.index('S') if 'S' in normalized_header else None
        mem_index = normalized_header.index('%MEM') if '%MEM' in normalized_header else None

        parts = re.split(r'\s+', line.strip(), maxsplit=command_index)
        if len(parts) <= max(cpu_index, command_index):
            raise ValueError('top 프로세스 라인의 컬럼 수가 부족합니다: ' + line)

        command_name = parts[command_index].strip() if command_index < len(parts) else ''
        if not process_pattern.search(line) and not process_pattern.search(command_name):
            return None

        if self._is_self_command_line(line):
            return None

        try:
            cpu_percent = float(str(parts[cpu_index]).strip())
        except Exception as exc:
            raise ValueError('CPU 사용률 숫자 변환 실패: ' + line) from exc

        memory_percent = None
        if mem_index is not None and mem_index < len(parts):
            try:
                memory_percent = float(str(parts[mem_index]).strip())
            except Exception:
                memory_percent = None

        return {
            'pid': parts[pid_index].strip() if pid_index < len(parts) else '',
            'user': parts[user_index].strip() if user_index < len(parts) else '',
            'state': parts[state_index].strip() if state_index is not None and state_index < len(parts) else '',
            'cpu_percent': cpu_percent,
            'memory_percent': memory_percent,
            'command_name': command_name,
            'raw_line': line.strip(),
        }

    def _parse_top_output(self, stdout, process_name):
        lines = [line.strip() for line in str(stdout or '').splitlines() if line.strip()]
        header_index, header_line, header_tokens = self._find_top_header(lines)
        if header_index is None:
            raise ValueError('top 출력에서 PID/%CPU/COMMAND 헤더 라인을 찾지 못했습니다.')

        normalized_header = [token.upper() for token in header_tokens]
        if '%CPU' not in normalized_header:
            raise ValueError('top 헤더에서 %CPU 컬럼을 찾지 못했습니다.')
        if 'COMMAND' not in normalized_header:
            raise ValueError('top 헤더에서 COMMAND 컬럼을 찾지 못했습니다.')

        try:
            process_pattern = re.compile(str(process_name or ''), re.IGNORECASE)
        except re.error as exc:
            raise ValueError('process_name 정규식이 올바르지 않습니다: ' + str(exc))

        processes = []
        for line in lines[header_index + 1:]:
            if line == header_line:
                continue
            parsed = self._parse_process_line(line, header_tokens, process_pattern)
            if parsed is not None:
                processes.append(parsed)

        return header_line, processes

    def run(self):
        thresholds = self._load_thresholds()
        process_name = thresholds['process_name']
        max_cpu_usage_percent = thresholds['max_cpu_usage_percent']

        threshold_result = {
            'process_name': process_name,
            'max_cpu_usage_percent': max_cpu_usage_percent,
            'failure_keywords': thresholds['failure_keywords'],
        }

        command = f"top -b -n 1 | grep -E {self._quote('PID|' + process_name)}"
        result = self._run_command(command, timeout=self.DEFAULT_COMMAND_TIMEOUT)
        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()

        metrics = self._base_metrics(command, result, stdout, stderr, thresholds)

        if max_cpu_usage_percent < 0:
            return self._fail(
                '임계치 오류',
                '프로세스 CPU 사용률 점검에 실패했습니다. max_cpu_usage_percent 값은 0 이상 숫자여야 합니다.',
                result,
                metrics,
                threshold_result,
                stdout,
                stderr,
                'max_cpu_usage_percent 값이 허용 범위를 벗어났습니다.',
            )

        if result.get('timed_out'):
            return self._fail(
                '점검 명령 timeout',
                '프로세스 CPU 사용률 점검에 실패했습니다. top 명령 실행 중 timeout이 발생했습니다.',
                result,
                metrics,
                threshold_result,
                stdout,
                stderr,
                '명령 실행 중 timeout이 발생했습니다.',
            )

        if result.get('rc') != 0:
            return self._fail(
                '점검 명령 실행 실패',
                f'프로세스 CPU 사용률 점검에 실패했습니다. top/grep 명령 종료코드가 rc={result.get("rc")}입니다.',
                result,
                metrics,
                threshold_result,
                stdout,
                stderr,
                f'명령 종료코드가 rc={result.get("rc")}입니다.',
            )

        failure_keyword = self._contains_failure_keyword(stdout, stderr)
        if failure_keyword:
            return self._fail(
                '점검 명령 실행 실패',
                f'프로세스 CPU 사용률 점검에 실패했습니다. 출력에서 실패 키워드가 확인되었습니다: {failure_keyword}',
                result,
                metrics,
                threshold_result,
                stdout,
                stderr,
                f'출력에서 실패 키워드가 확인되었습니다: {failure_keyword}',
            )

        if not stdout:
            return self._fail(
                '대상 프로세스 없음',
                f'프로세스 CPU 사용률 점검에 실패했습니다. process_name={process_name} 기준 대상 프로세스를 찾지 못했습니다.',
                result,
                metrics,
                threshold_result,
                stdout,
                stderr,
                '대상 프로세스가 없거나 top 출력이 비어 있습니다.',
            )

        try:
            top_header_line, processes = self._parse_top_output(stdout, process_name)
        except Exception as exc:
            metrics['top_header_line'] = ''
            return self._fail(
                'top 출력 파싱 실패',
                '프로세스 CPU 사용률 점검에 실패했습니다. 대상 프로세스가 없거나 top 출력에서 %CPU 컬럼을 파싱하지 못해 CPU 사용률을 판단하지 못했습니다.',
                result,
                metrics,
                threshold_result,
                stdout,
                stderr,
                str(exc),
            )

        metrics['top_header_line'] = top_header_line
        metrics['processes'] = processes
        metrics['process_count'] = len(processes)
        metrics['first_process_line'] = processes[0]['raw_line'] if processes else ''

        if not processes:
            return self._fail(
                '대상 프로세스 없음',
                f'프로세스 CPU 사용률 점검에 실패했습니다. process_name={process_name} 기준 대상 프로세스를 찾지 못했습니다.',
                result,
                metrics,
                threshold_result,
                stdout,
                stderr,
                '대상 프로세스가 없습니다.',
            )

        highest_process = max(processes, key=lambda item: item.get('cpu_percent', 0.0))
        over_threshold = [
            item for item in processes
            if item.get('cpu_percent', 0.0) > max_cpu_usage_percent
        ]

        metrics['max_observed_cpu_percent'] = highest_process.get('cpu_percent')
        metrics['highest_cpu_process_line'] = highest_process.get('raw_line', '')
        metrics['over_threshold_count'] = len(over_threshold)
        metrics['over_threshold_lines'] = [
            item.get('raw_line', '')
            for item in over_threshold[:20]
        ]

        if over_threshold:
            message = (
                '프로세스 CPU 사용률 점검 결과 경고입니다. '
                f'process_name={process_name} 기준 대상 프로세스 {len(processes)}건 중 '
                f'{len(over_threshold)}건이 CPU 기준 {max_cpu_usage_percent:.1f}%를 초과했습니다. '
                f'최대 CPU 사용률은 {highest_process.get("cpu_percent", 0.0):.1f}%입니다.'
            )
            return self.warn(
                metrics=metrics,
                thresholds=threshold_result,
                reasons='대상 프로세스 중 CPU 사용률 기준을 초과한 프로세스가 있습니다.',
                message=message,
            )

        message = (
            '프로세스 CPU 사용률 점검 결과 정상입니다. '
            f'process_name={process_name} 기준 대상 프로세스 {len(processes)}건이 확인되었고, '
            f'최대 CPU 사용률은 {highest_process.get("cpu_percent", 0.0):.1f}%로 기준 {max_cpu_usage_percent:.1f}% 이하입니다.'
        )
        return self.ok(
            metrics=metrics,
            thresholds=threshold_result,
            reasons='모든 대상 프로세스의 CPU 사용률이 기준 이하입니다.',
            message=message,
        )


CHECK_CLASS = Check
