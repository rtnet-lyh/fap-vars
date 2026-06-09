# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


COMMAND = 'ps -eo pid,stat,comm'
COMMAND_TIMEOUT = 20
TOP_PROCESS_LIMIT = 20


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'linux'
    PARAMIKO_REUSE_SESSION = False

    def _run_command(self):
        result = self._run_paramiko_commands(
            [{'command': COMMAND, 'timeout': COMMAND_TIMEOUT}],
            become=True,
            profile='linux',
        )[0]
        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()
        if result.get('rc') != 0:
            return stdout, stderr, self.fail(
                '점검 명령 실행 실패',
                message='Apache Tomcat 프로세스 상태 점검 명령 실행에 실패했습니다.',
                stdout=stdout,
                stderr=stderr,
            )
        return stdout, stderr, None

    def _bad_state_set(self):
        raw_states = self.get_threshold_var('bad_states', default='Z,D,T', value_type='str')
        return {
            value.strip().upper()
            for value in re.split(r'[,|]+', raw_states)
            if value.strip()
        }

    def _parse_rows(self, stdout):
        rows = []
        header_found = False
        for line in stdout.splitlines():
            parts = line.strip().split()
            if not parts:
                continue
            if 'PID' in parts and 'STAT' in parts and 'COMMAND' in parts:
                header_found = True
                continue
            if not header_found or len(parts) < 3:
                continue
            try:
                pid = int(parts[0])
            except ValueError:
                continue
            rows.append({
                'pid': pid,
                'stat': parts[1],
                'command': ' '.join(parts[2:]),
            })
        return rows

    def run(self):
        stdout, _stderr, error = self._run_command()
        if error:
            return error

        rows = self._parse_rows(stdout)
        if not rows:
            return self.fail(
                '프로세스 상태 파싱 실패',
                message='ps 출력에서 프로세스 상태 정보를 해석할 수 없습니다.',
                stdout=stdout,
            )

        bad_states = self._bad_state_set()
        bad_rows = [
            row for row in rows
            if (row.get('stat') or '').upper()[:1] in bad_states
        ]
        metrics = {
            'process_count': len(rows),
            'states': sorted({row['stat'] for row in rows}),
            'bad_process_count': len(bad_rows),
            'bad_processes': bad_rows,
            'sample_processes': rows[:TOP_PROCESS_LIMIT],
        }
        thresholds = {'bad_process_states': sorted(bad_states)}
        if bad_rows:
            return self.warn(
                metrics=metrics,
                thresholds=thresholds,
                reasons='비정상 프로세스 상태가 발견되었습니다.',
                message='Apache Tomcat 프로세스 상태 경고: 비정상 상태 %s건' % len(bad_rows),
            )
        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='프로세스 상태에 Z/D/T 상태가 없습니다.',
            message='Apache Tomcat 프로세스 상태 정상: 상태=%s' % ','.join(metrics['states']),
        )


CHECK_CLASS = Check
