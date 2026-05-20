# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'linux'
    PARAMIKO_REUSE_SESSION = False

    DEFAULT_PROCESS_NAME = 'exTMS'
    DEFAULT_BAD_PROCESS_STATES = 'Z,D,T'
    COMMAND_TIMEOUT = 10

    def _parse_bad_states(self, raw_value):
        return {
            token.strip().upper()
            for token in re.split(r'[,| ]+', str(raw_value or ''))
            if token.strip()
        }

    def _parse_ps_rows(self, stdout):
        rows = []
        for line in str(stdout or '').splitlines():
            parts = re.split(r'\s+', line.strip(), maxsplit=10)
            if len(parts) < 11 or not parts[1].isdigit():
                continue
            try:
                rows.append({
                    'user': parts[0],
                    'pid': parts[1],
                    'cpu_percent': float(parts[2]),
                    'mem_percent': float(parts[3]),
                    'stat': parts[7],
                    'start': parts[8],
                    'time': parts[9],
                    'command': parts[10],
                })
            except (ValueError, IndexError):
                continue
        return rows

    def run(self):
        process_name = self.get_host_var(key='process_name')        
        if not process_name:
            process_name = self.get_threshold_var(
                'process_name', 
                default=self.DEFAULT_PROCESS_NAME, 
                value_type='str'
            ).strip()

        bad_states_raw = self.get_threshold_var(
            'bad_process_states',
            default=self.DEFAULT_BAD_PROCESS_STATES,
            value_type='str',
        )
        bad_states = self._parse_bad_states(bad_states_raw)
        command = 'ps aux | grep %s | grep -v grep' % process_name

        result = self._run_paramiko_commands(
            [{'command': command, 'timeout': self.COMMAND_TIMEOUT}],
            become=True,
            profile='linux',
        )[0]

        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()
        if result.get('rc') != 0:
            return self.fail(
                'ps 명령 실행 실패',
                message='WEB 프로세스 기동 상태를 확인하지 못했습니다.',
                stdout=stdout,
                stderr=stderr,
            )

        rows = self._parse_ps_rows(stdout)
        if not rows:
            return self.fail(
                '프로세스 정보 없음',
                message='ps 출력에서 대상 프로세스를 찾지 못했습니다.',
                stdout=stdout,
                stderr=stderr,
            )

        bad_rows = [
            row for row in rows
            if any(state in (row['stat'] or '').upper() for state in bad_states)
        ]

        metrics = {
            'process_name': process_name,
            'process_count': len(rows),
            'pids': [row['pid'] for row in rows],
            'states': sorted({row['stat'] for row in rows}),
            'bad_process_count': len(bad_rows),
            'bad_processes': bad_rows,
            'processes': rows,
        }
        thresholds = {
            'process_name': process_name,
            'bad_process_states': sorted(bad_states),
        }

        if bad_rows:
            return self.warn(
                metrics=metrics,
                thresholds=thresholds,
                reasons='기동 중인 WEB 프로세스에서 비정상 상태가 발견되었습니다.',
                message='WEB 프로세스 기동 경고: 비정상 상태 %s건, 기준 %s' % (
                    len(bad_rows),
                    ','.join(sorted(bad_states)),
                ),
            )

        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='유효한 PID가 있고 비정상 상태 코드가 없습니다.',
            message='WEB 프로세스 기동 정상: %s개 프로세스 PID=%s' % (
                len(rows),
                ','.join(metrics['pids']),
            ),
        )


CHECK_CLASS = Check
