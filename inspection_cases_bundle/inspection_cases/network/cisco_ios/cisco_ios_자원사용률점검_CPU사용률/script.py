# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


CPU_USAGE_COMMAND = 'show processes cpu sorted'
CPU_LINE_PATTERN = re.compile(
    r'^CPU utilization for five seconds:\s*'
    r'(?P<five_sec>[0-9]+(?:\.[0-9]+)?)%'
    r'(?:/(?P<interrupt>[0-9]+(?:\.[0-9]+)?)%)?;\s*'
    r'one minute:\s*(?P<one_min>[0-9]+(?:\.[0-9]+)?)%;\s*'
    r'five minutes:\s*(?P<five_min>[0-9]+(?:\.[0-9]+)?)%\s*$',
    re.IGNORECASE,
)
PROCESS_LINE_PATTERN = re.compile(
    r'^\s*(?P<pid>\d+)\s+'
    r'(?P<runtime_ms>\d+)\s+'
    r'(?P<invoked>\d+)\s+'
    r'(?P<usecs>\d+)\s+'
    r'(?P<five_sec>[0-9]+(?:\.[0-9]+)?)%\s+'
    r'(?P<one_min>[0-9]+(?:\.[0-9]+)?)%\s+'
    r'(?P<five_min>[0-9]+(?:\.[0-9]+)?)%\s+'
    r'(?P<tty>\S+)\s+'
    r'(?P<process>.+?)\s*$'
)


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'cisco_ios'

    def _get_credential_value(self, key, default=None):
        value = self.get_connection_value(key, None)
        if value not in (None, ''):
            return value
        return self.get_application_credential_value(key, default)

    def _is_enable_requested(self):
        become_raw = self._get_credential_value('become', False)
        return str(become_raw).strip().lower() in ('1', 'true', 'y', 'yes', 'on')

    def _build_command_items(self):
        command_items = []

        if self._is_enable_requested():
            become_password = str(self._get_credential_value('become_password', '') or '')
            if not become_password:
                return None, self.fail(
                    'enable 비밀번호 없음',
                    message='connection credential data에 become_password가 필요합니다.',
                )
            command_items.extend([
                {
                    'command': 'enable',
                    'ignore_prompt': True,
                },
                {
                    'command': become_password,
                    'hide_command': True,
                },
            ])

        command_items.extend([
            {
                'command': 'terminal length 0',
            },
            {
                'command': CPU_USAGE_COMMAND,
            },
        ])
        return command_items, None

    def _run_commands(self):
        command_items, error = self._build_command_items()
        if error:
            return None, error

        results = self._run_paramiko_commands(command_items)
        failed = [
            item for item in results
            if item.get('rc') != 0 and not (item.get('command') == 'enable' and item.get('timed_out'))
        ]
        if failed:
            first = failed[0]
            display_command = first.get('display_command') or first.get('command')
            return None, self.fail(
                '점검 명령 실행 실패',
                message=f'{display_command} 명령 실행에 실패했습니다.',
                stdout=(first.get('stdout') or '').strip(),
                stderr=(first.get('stderr') or '').strip(),
            )

        return results, None

    def _parse_cpu_header(self, text):
        for raw_line in (text or '').splitlines():
            line = raw_line.strip()
            if not line:
                continue
            match = CPU_LINE_PATTERN.match(line)
            if match:
                return {
                    'cpu_usage_5sec_percent': round(float(match.group('five_sec')), 2),
                    'cpu_usage_5sec_interrupt_percent': round(float(match.group('interrupt') or 0.0), 2),
                    'cpu_usage_1min_percent': round(float(match.group('one_min')), 2),
                    'cpu_usage_5min_percent': round(float(match.group('five_min')), 2),
                }
        return None

    def _parse_top_processes(self, text, limit=5):
        processes = []
        for raw_line in (text or '').splitlines():
            match = PROCESS_LINE_PATTERN.match(raw_line.rstrip())
            if not match:
                continue
            processes.append({
                'pid': int(match.group('pid')),
                'runtime_ms': int(match.group('runtime_ms')),
                'invoked': int(match.group('invoked')),
                'usecs': int(match.group('usecs')),
                'cpu_5sec_percent': round(float(match.group('five_sec')), 2),
                'cpu_1min_percent': round(float(match.group('one_min')), 2),
                'cpu_5min_percent': round(float(match.group('five_min')), 2),
                'tty': match.group('tty'),
                'process': match.group('process').strip(),
            })
            if len(processes) >= limit:
                break
        return processes

    # def _serialize_command_results(self, results):
    #     serialized = []
    #     for item in results:
    #         serialized.append({
    #             'command': item.get('command'),
    #             'display_command': item.get('display_command') or item.get('command'),
    #             'rc': item.get('rc'),
    #             'stdout': item.get('stdout') or '',
    #             'stderr': item.get('stderr') or '',
    #             'raw_output': item.get('raw_output') or '',
    #             'timed_out': bool(item.get('timed_out')),
    #             'prompt': item.get('prompt') or '',
    #         })
    #     return serialized

    def run(self):
        max_cpu_usage_percent = self.get_threshold_var(
            'max_cpu_usage_percent',
            default=80.0,
            value_type='float',
        )
        results, error = self._run_commands()
        if error:
            return error

        if not results:
            return self.fail(
                '점검 결과 없음',
                message='Cisco IOS CPU 사용률 점검 결과가 비어 있습니다.',
            )

        cpu_output = (results[-1].get('stdout') or '').strip()
        if not cpu_output:
            return self.fail(
                'CPU 출력 없음',
                message='show processes cpu sorted 결과가 비어 있습니다.',
                stdout='',
            )

        parsed = self._parse_cpu_header(cpu_output)
        if not parsed:
            return self.fail(
                'CPU 사용률 파싱 실패',
                message='show processes cpu sorted 첫 줄에서 CPU 사용률을 해석하지 못했습니다.',
                stdout=cpu_output,
            )

        top_processes = self._parse_top_processes(cpu_output)
        metrics = {
            'cpu_usage_5sec_percent': parsed['cpu_usage_5sec_percent'],
            'cpu_usage_5sec_interrupt_percent': parsed['cpu_usage_5sec_interrupt_percent'],
            'cpu_usage_1min_percent': parsed['cpu_usage_1min_percent'],
            'cpu_usage_5min_percent': parsed['cpu_usage_5min_percent'],
            'top_processes': top_processes,
        }
        thresholds = {
            'max_cpu_usage_percent': max_cpu_usage_percent,
        }

        if parsed['cpu_usage_5min_percent'] > max_cpu_usage_percent:
            return self.fail(
                'CPU 사용률 임계치 초과',
                message=(
                    'Cisco IOS CPU 사용률이 기준치를 초과했습니다. '
                    f'5분 평균 CPU 사용률 {parsed["cpu_usage_5min_percent"]}%가 '
                    f'임계치 {max_cpu_usage_percent}%보다 큽니다.'
                ),
                stdout=cpu_output,
            )

        if (
            parsed['cpu_usage_5sec_percent'] > max_cpu_usage_percent
            or parsed['cpu_usage_1min_percent'] > max_cpu_usage_percent
        ):
            return self.warn(
                metrics=metrics,
                thresholds=thresholds,
                reasons=(
                    f'5초 CPU 사용률 {parsed["cpu_usage_5sec_percent"]}% 또는 '
                    f'1분 CPU 사용률 {parsed["cpu_usage_1min_percent"]}%가 임계치 '
                    f'{max_cpu_usage_percent}%를 초과했지만 5분 평균 '
                    f'{parsed["cpu_usage_5min_percent"]}%는 기준 이내입니다.'
                ),
                message=(
                    'Cisco IOS CPU 사용률이 단기적으로 높습니다. '
                    f'5초={parsed["cpu_usage_5sec_percent"]}%, '
                    f'1분={parsed["cpu_usage_1min_percent"]}%, '
                    f'5분={parsed["cpu_usage_5min_percent"]}%, '
                    f'기준={max_cpu_usage_percent}%.'
                ),
            )

        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons=(
                f'5분 평균 CPU 사용률 {parsed["cpu_usage_5min_percent"]}%가 '
                f'임계치 {max_cpu_usage_percent}% 이하입니다.'
            ),
            message=(
                'Cisco IOS CPU 사용률 점검이 정상 수행되었습니다. '
                f'5초={parsed["cpu_usage_5sec_percent"]}%, '
                f'1분={parsed["cpu_usage_1min_percent"]}%, '
                f'5분={parsed["cpu_usage_5min_percent"]}%, '
                f'기준={max_cpu_usage_percent}%.'
            ),
        )


CHECK_CLASS = Check
