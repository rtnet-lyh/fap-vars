# -*- coding: utf-8 -*-

import math
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
        combined = '\n'.join(str(text or '') for text in texts if text is not None)
        lowered = combined.lower()
        for keyword in self._get_failure_keywords():
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
        process_name = self.get_threshold_var(
            'process_name',
            default='wsm|htl|hth',
            value_type='str',
        )
        max_mem_usage_percent = self.get_threshold_var(
            'max_mem_usage_percent',
            default=70,
            value_type='float',
        )
        failure_keywords = self._get_failure_keywords()
        return {
            'process_name': process_name,
            'max_mem_usage_percent': max_mem_usage_percent,
            'failure_keywords': failure_keywords,
        }

    def _base_metrics(self, result, command, thresholds, stdout=None, stderr=None):
        out = result.get('stdout') if stdout is None else stdout
        err = result.get('stderr') if stderr is None else stderr
        return {
            'command': command,
            'command_rc': result.get('rc'),
            'timed_out': bool(result.get('timed_out', False)),
            'stdout_line_count': self._line_count(out),
            'stderr_line_count': self._line_count(err),
            'process_name': thresholds.get('process_name'),
            'max_mem_usage_percent': thresholds.get('max_mem_usage_percent'),
            'process_count': 0,
            'max_observed_mem_percent': None,
            'over_threshold_count': 0,
            'top_header_line': '',
            'first_process_line': '',
            'highest_mem_process_line': '',
            'over_threshold_lines': [],
            'processes': [],
        }

    def _fail_result(self, error, message, result, command, thresholds, stdout='', stderr='', reasons=''):
        metrics = self._base_metrics(result, command, thresholds, stdout=stdout, stderr=stderr)
        return self.fail(
            error,
            message=message,
            stdout=(stdout or '').strip(),
            stderr=(stderr or '').strip(),
            metrics=metrics,
            thresholds=thresholds,
            reasons=reasons or message,
        )

    def _find_top_header(self, lines):
        for line in lines:
            tokens = re.split(r'\s+', line.strip())
            if not tokens:
                continue
            normalized = [token.upper() for token in tokens]
            if 'PID' in normalized and '%MEM' in normalized and 'COMMAND' in normalized:
                return line, tokens
        return '', []

    def _header_index(self, header_tokens, name):
        target = str(name or '').upper()
        for index, token in enumerate(header_tokens):
            if str(token or '').upper() == target:
                return index
        return -1

    def _is_self_command_line(self, raw_line, command_name):
        raw_lower = str(raw_line or '').lower()
        command_lower = str(command_name or '').strip().lower()
        if command_lower in ('grep', 'egrep', 'top'):
            return True
        self_markers = (
            'grep -e',
            'egrep ',
            'top -b -n 1',
        )
        return any(marker in raw_lower for marker in self_markers)

    def _parse_process_line(self, raw_line, header_indexes):
        parts = re.split(r'\s+', str(raw_line or '').strip())
        mem_idx = header_indexes.get('mem')
        cpu_idx = header_indexes.get('cpu')
        command_idx = header_indexes.get('command')
        pid_idx = header_indexes.get('pid')
        user_idx = header_indexes.get('user')
        state_idx = header_indexes.get('state')

        required_indexes = [pid_idx, user_idx, mem_idx, command_idx]
        if any(index is None or index < 0 or index >= len(parts) for index in required_indexes):
            return None, '프로세스 라인의 필수 컬럼 수가 부족합니다.'

        command_name = ' '.join(parts[command_idx:]).strip()
        if not command_name:
            return None, 'COMMAND 컬럼 값이 비어 있습니다.'

        try:
            memory_percent = float(parts[mem_idx])
        except Exception:
            return None, '프로세스 라인의 %MEM 값을 숫자로 변환하지 못했습니다.'

        cpu_percent = None
        if cpu_idx is not None and 0 <= cpu_idx < len(parts):
            try:
                cpu_percent = float(parts[cpu_idx])
            except Exception:
                cpu_percent = None

        state = ''
        if state_idx is not None and 0 <= state_idx < len(parts):
            state = parts[state_idx]

        return {
            'pid': parts[pid_idx],
            'user': parts[user_idx],
            'state': state,
            'cpu_percent': cpu_percent,
            'memory_percent': memory_percent,
            'command_name': command_name,
            'raw_line': raw_line,
        }, ''

    def _parse_top_output(self, stdout, process_pattern):
        lines = [line.rstrip() for line in str(stdout or '').splitlines() if line.strip()]
        header_line, header_tokens = self._find_top_header(lines)
        if not header_line:
            return None, 'top 출력에서 PID/%MEM/COMMAND 헤더 라인을 찾지 못했습니다.'

        pid_idx = self._header_index(header_tokens, 'PID')
        user_idx = self._header_index(header_tokens, 'USER')
        state_idx = self._header_index(header_tokens, 'S')
        cpu_idx = self._header_index(header_tokens, '%CPU')
        mem_idx = self._header_index(header_tokens, '%MEM')
        command_idx = self._header_index(header_tokens, 'COMMAND')

        if mem_idx < 0:
            return None, 'top 출력 헤더에서 %MEM 컬럼을 찾지 못했습니다.'
        if command_idx < 0:
            return None, 'top 출력 헤더에서 COMMAND 컬럼을 찾지 못했습니다.'
        if pid_idx < 0 or user_idx < 0:
            return None, 'top 출력 헤더에서 PID 또는 USER 컬럼을 찾지 못했습니다.'

        header_indexes = {
            'pid': pid_idx,
            'user': user_idx,
            'state': state_idx,
            'cpu': cpu_idx,
            'mem': mem_idx,
            'command': command_idx,
        }

        processes = []
        parsing_error = ''
        for line in lines:
            if line == header_line:
                continue
            parsed, error = self._parse_process_line(line, header_indexes)
            if parsed is None:
                if not parsing_error:
                    parsing_error = error
                continue
            if self._is_self_command_line(line, parsed.get('command_name')):
                continue
            if not process_pattern.search(parsed.get('command_name') or ''):
                continue
            if error:
                return None, error
            processes.append(parsed)

        if not processes:
            return {
                'top_header_line': header_line,
                'processes': [],
                'parsing_error': parsing_error,
            }, ''

        return {
            'top_header_line': header_line,
            'processes': processes,
            'parsing_error': parsing_error,
        }, ''

    def run(self):
        thresholds = self._load_thresholds()
        process_name = str(thresholds.get('process_name') or '').strip() or 'wsm|htl|hth'
        max_mem_usage_percent = thresholds.get('max_mem_usage_percent')
        thresholds['process_name'] = process_name

        command = f"top -b -n 1 | grep -E {self._quote('PID|' + process_name)}"
        empty_result = {
            'command': command,
            'rc': None,
            'stdout': '',
            'stderr': '',
            'timed_out': False,
        }

        if not isinstance(max_mem_usage_percent, (int, float)) or not math.isfinite(float(max_mem_usage_percent)) or float(max_mem_usage_percent) < 0:
            return self._fail_result(
                '임계치 오류',
                '프로세스 메모리 사용률 점검에 실패했습니다. max_mem_usage_percent 값이 0 이상 숫자가 아닙니다.',
                empty_result,
                command,
                thresholds,
                stdout='',
                stderr='',
                reasons='max_mem_usage_percent 값 오류',
            )
        thresholds['max_mem_usage_percent'] = float(max_mem_usage_percent)

        try:
            process_pattern = re.compile(process_name)
        except Exception as exc:
            return self._fail_result(
                '임계치 오류',
                f'프로세스 메모리 사용률 점검에 실패했습니다. process_name 정규식이 올바르지 않습니다: {exc}',
                empty_result,
                command,
                thresholds,
                stdout='',
                stderr=str(exc),
                reasons='process_name 정규식 오류',
            )

        result = self._run_command(command, timeout=self.DEFAULT_COMMAND_TIMEOUT)
        rc = result.get('rc')
        out = (result.get('stdout') or '').strip()
        err = (result.get('stderr') or '').strip()
        metrics = self._base_metrics(result, command, thresholds, stdout=out, stderr=err)

        if result.get('timed_out'):
            return self.fail(
                '점검 명령 timeout',
                message=(
                    '프로세스 메모리 사용률 점검에 실패했습니다. '
                    'top -b -n 1 명령 실행 중 timeout이 발생했습니다.'
                ),
                stdout=out,
                stderr=err,
                metrics=metrics,
                thresholds=thresholds,
                reasons='명령 실행 timeout',
            )

        if rc != 0:
            if rc == 1:
                message = (
                    '프로세스 메모리 사용률 점검에 실패했습니다. '
                    f'process_name={process_name} 기준 대상 프로세스가 없거나 top 출력에서 대상 프로세스를 찾지 못했습니다.'
                )
                reason = '대상 프로세스 없음 또는 grep 결과 없음'
            else:
                message = (
                    '프로세스 메모리 사용률 점검에 실패했습니다. '
                    f'top/grep 명령 종료코드가 rc={rc}입니다.'
                )
                reason = f'명령 종료코드 rc={rc}'
            return self.fail(
                '점검 명령 실행 실패',
                message=message,
                stdout=out,
                stderr=err,
                metrics=metrics,
                thresholds=thresholds,
                reasons=reason,
            )

        failure_keyword = self._contains_failure_keyword(out, err)
        if failure_keyword:
            return self.fail(
                '점검 명령 실행 실패',
                message=(
                    '프로세스 메모리 사용률 점검에 실패했습니다. '
                    f'명령 출력에서 실패 키워드가 확인되었습니다: {failure_keyword}'
                ),
                stdout=out,
                stderr=err,
                metrics=metrics,
                thresholds=thresholds,
                reasons=f'실패 키워드 감지: {failure_keyword}',
            )

        if not out:
            return self.fail(
                '점검 출력 없음',
                message=(
                    '프로세스 메모리 사용률 점검에 실패했습니다. '
                    f'process_name={process_name} 기준 대상 프로세스가 없거나 top 출력이 비어 있어 메모리 사용률을 판단하지 못했습니다.'
                ),
                stdout=out,
                stderr=err,
                metrics=metrics,
                thresholds=thresholds,
                reasons='출력 없음 또는 대상 프로세스 없음',
            )

        parsed, parse_error = self._parse_top_output(out, process_pattern)
        if parse_error:
            return self.fail(
                'top 출력 파싱 실패',
                message=(
                    '프로세스 메모리 사용률 점검에 실패했습니다. '
                    f'{parse_error}'
                ),
                stdout=out,
                stderr=err,
                metrics=metrics,
                thresholds=thresholds,
                reasons=parse_error,
            )

        processes = parsed.get('processes') or []
        metrics['top_header_line'] = parsed.get('top_header_line') or ''
        metrics['processes'] = processes
        metrics['process_count'] = len(processes)

        if not processes:
            return self.fail(
                '대상 프로세스 없음',
                message=(
                    '프로세스 메모리 사용률 점검에 실패했습니다. '
                    f'process_name={process_name} 기준 대상 프로세스가 없거나 top 출력에서 대상 프로세스를 찾지 못했습니다.'
                ),
                stdout=out,
                stderr=err,
                metrics=metrics,
                thresholds=thresholds,
                reasons='대상 프로세스 없음',
            )

        highest = max(processes, key=lambda item: item.get('memory_percent', 0.0))
        over_threshold = [
            item for item in processes
            if float(item.get('memory_percent') or 0.0) > float(max_mem_usage_percent)
        ]

        metrics.update({
            'first_process_line': processes[0].get('raw_line') or '',
            'highest_mem_process_line': highest.get('raw_line') or '',
            'max_observed_mem_percent': highest.get('memory_percent'),
            'over_threshold_count': len(over_threshold),
            'over_threshold_lines': [item.get('raw_line') or '' for item in over_threshold[:20]],
        })

        if over_threshold:
            message = (
                '프로세스 메모리 사용률 점검 결과 경고입니다. '
                f'process_name={process_name} 기준 대상 프로세스 {len(processes)}건 중 '
                f'{len(over_threshold)}건이 메모리 기준 {float(max_mem_usage_percent):.1f}%를 초과했습니다. '
                f'최대 메모리 사용률은 {float(highest.get("memory_percent") or 0.0):.1f}%입니다. '
                f'기준 초과 또는 최대 사용 프로세스: {highest.get("raw_line") or ""}'
            )
            return self.warn(
                metrics=metrics,
                thresholds=thresholds,
                reasons='대상 프로세스 중 메모리 사용률 기준 초과 항목이 확인되었습니다.',
                message=message,
            )

        message = (
            '프로세스 메모리 사용률 점검 결과 정상입니다. '
            f'process_name={process_name} 기준 대상 프로세스 {len(processes)}건이 확인되었고, '
            f'최대 메모리 사용률은 {float(highest.get("memory_percent") or 0.0):.1f}%로 '
            f'기준 {float(max_mem_usage_percent):.1f}% 이하입니다.'
        )
        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='모든 대상 프로세스의 메모리 사용률이 기준 이하입니다.',
            message=message,
        )


CHECK_CLASS = Check
