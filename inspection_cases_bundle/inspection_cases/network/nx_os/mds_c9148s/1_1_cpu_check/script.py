# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


CPU_USAGE_COMMAND = 'show processes cpu sort'
HEADER_RE = re.compile(r'\bPID\b.*\b5Sec\b.*\b1Min\b.*\b5Min\b.*\bProcess\b')
PROCESS_RE = re.compile(
    r'^\s*(?P<pid>\d+)\s+\d+\s+\d+\s+\d+\s+'
    r'(?P<cpu_5sec>[0-9.]+)%\s+(?P<cpu_1min>[0-9.]+)%\s+'
    r'(?P<cpu_5min>[0-9.]+)%\s+\S+\s+(?P<process>.+?)\s*$'
)
PROMPT_RE = re.compile(r'^[A-Za-z0-9_.:/-]+[>#]\s*$')


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def _parse_top_processes(self, text, limit):
        found_header = False
        processes = []
        invalid_rows = []

        for line in (text or '').splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if not found_header:
                found_header = bool(HEADER_RE.search(stripped))
                continue
            if set(stripped) <= {'-', ' '} or PROMPT_RE.match(stripped):
                continue

            match = PROCESS_RE.match(stripped)
            if not match:
                invalid_rows.append(stripped)
                continue

            processes.append({
                'pid': int(match.group('pid')),
                'process': match.group('process').strip(),
                'cpu_5sec_percent': round(float(match.group('cpu_5sec')), 2),
                'cpu_1min_percent': round(float(match.group('cpu_1min')), 2),
                'cpu_5min_percent': round(float(match.group('cpu_5min')), 2),
            })
            if len(processes) >= limit:
                break

        return found_header, processes, invalid_rows

    def run(self):
        max_cpu_usage_percent = self.get_threshold_var(
            'max_cpu_usage_percent',
            default=80.0,
            value_type='float',
        )
        top_process_count = max(1, self.get_threshold_var(
            'top_process_count',
            default=5,
            value_type='int',
        ))
        thresholds = {
            'max_cpu_usage_percent': max_cpu_usage_percent,
            'top_process_count': top_process_count,
        }

        rc, out, err = self._ssh(CPU_USAGE_COMMAND)
        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='show processes cpu sort 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
                thresholds=thresholds,
            )

        output = (out or '').strip()
        table_found, top_processes, invalid_rows = self._parse_top_processes(output, top_process_count)
        if not table_found or not top_processes or invalid_rows:
            return self.fail(
                '프로세스 행 파싱 실패',
                message='프로세스 테이블의 5Min CPU 사용률을 해석하지 못했습니다.',
                stdout=output,
                metrics={'top_processes': top_processes, 'invalid_rows': invalid_rows},
                thresholds=thresholds,
            )

        max_process = max(top_processes, key=lambda item: item['cpu_5min_percent'])
        over_threshold = [
            item for item in top_processes
            if item['cpu_5min_percent'] > max_cpu_usage_percent
        ]
        metrics = {
            'collected_process_count': len(top_processes),
            'max_cpu_5min_percent': max_process['cpu_5min_percent'],
            'max_cpu_process': max_process,
            'over_threshold_processes': over_threshold,
            'top_processes': top_processes,
        }

        if over_threshold:
            return self.fail(
                'CPU 사용률 임계치 초과',
                message=(
                    f'상위 {len(top_processes)}개 프로세스 중 5Min CPU 사용률이 '
                    f'{max_cpu_usage_percent}%를 초과한 항목이 있습니다.'
                ),
                stdout=output,
                metrics=metrics,
                thresholds=thresholds,
            )

        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons=(
                f'상위 {len(top_processes)}개 프로세스의 5Min CPU 사용률 최대값 '
                f'{max_process["cpu_5min_percent"]}%가 임계치 {max_cpu_usage_percent}% 이하입니다.'
            ),
            message=(
                f'CPU 사용률 점검이 정상 수행되었습니다. '
                f'최대 5Min={max_process["cpu_5min_percent"]}%, 기준={max_cpu_usage_percent}%.'
            ),
        )


CHECK_CLASS = Check
