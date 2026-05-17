# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'linux'
    PARAMIKO_REUSE_SESSION = False

    DEFAULT_PROCESS_NAME = 'exTMS'
    DEFAULT_MAX_CPU_USAGE_PERCENT = 70.0
    COMMAND_TIMEOUT = 10

    def _parse_top_rows(self, stdout):
        header = []
        rows = []
        for line in str(stdout or '').splitlines():
            parts = re.split(r'\s+', line.strip())
            if not parts or parts == ['']:
                continue
            if 'PID' in parts and '%CPU' in parts and '%MEM' in parts:
                header = parts
                continue
            if not header or len(parts) < len(header):
                continue

            try:
                row = {
                    'pid': parts[header.index('PID')],
                    'user': parts[header.index('USER')],
                    'state': parts[header.index('S')],
                    'cpu_percent': float(parts[header.index('%CPU')]),
                    'mem_percent': float(parts[header.index('%MEM')]),
                    'command': parts[header.index('COMMAND')],
                }
            except (ValueError, IndexError):
                continue
            rows.append(row)
        return rows

    def run(self):
        process_name = str(
            self.get_threshold_var('process_name', default=self.DEFAULT_PROCESS_NAME, value_type='str') or ''
        ).strip() or self.DEFAULT_PROCESS_NAME
        max_cpu_usage_percent = self.get_threshold_var(
            'max_cpu_usage_percent',
            default=self.DEFAULT_MAX_CPU_USAGE_PERCENT,
            value_type='float',
        )
        command = 'top -b -n 1 | egrep "PID|%s"' % process_name

        result = self._run_paramiko_commands(
            [{'command': command, 'timeout': self.COMMAND_TIMEOUT}],
            become=True,
            profile='linux',
        )[0]

        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()
        if result.get('rc') != 0:
            return self.fail(
                'top 명령 실행 실패',
                message='WEB 프로세스 CPU 사용률을 확인하지 못했습니다.',
                stdout=stdout,
                stderr=stderr,
            )

        rows = self._parse_top_rows(stdout)
        if not rows:
            return self.fail(
                '프로세스 정보 없음',
                message='top 출력에서 대상 프로세스를 찾지 못했습니다.',
                stdout=stdout,
                stderr=stderr,
            )

        max_row = max(rows, key=lambda row: row['cpu_percent'])
        over_rows = [row for row in rows if row['cpu_percent'] > max_cpu_usage_percent]
        metrics = {
            'process_name': process_name,
            'process_count': len(rows),
            'max_cpu_usage_percent': max_row['cpu_percent'],
            'max_cpu_pid': max_row['pid'],
            'max_cpu_command': max_row['command'],
            'over_threshold_count': len(over_rows),
            'processes': rows,
        }
        thresholds = {
            'process_name': process_name,
            'max_cpu_usage_percent': max_cpu_usage_percent,
        }

        if over_rows:
            return self.warn(
                metrics=metrics,
                thresholds=thresholds,
                reasons='CPU 사용률 기준 초과 프로세스가 있습니다.',
                message='WEB 프로세스 CPU 사용률 경고: 최대 %.1f%%, 기준 %.1f%%' % (
                    max_row['cpu_percent'],
                    max_cpu_usage_percent,
                ),
            )

        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='대상 프로세스 CPU 사용률이 기준 이하입니다.',
            message='WEB 프로세스 CPU 사용률 정상: 최대 %.1f%%, 기준 %.1f%%' % (
                max_row['cpu_percent'],
                max_cpu_usage_percent,
            ),
        )


CHECK_CLASS = Check
