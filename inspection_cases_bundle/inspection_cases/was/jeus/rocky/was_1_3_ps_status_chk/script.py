# -*- coding: utf-8 -*-

from .common._base import BaseCheck
import re

COMMAND = 'top -b -n 1 | egrep "PID|{process_name}"'
DEFAULT_PROCESS_NAME = 'exTMS'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'linux'
    PARAMIKO_REUSE_SESSION = False

    COMMAND_TIMEOUT = 20

    def _run_jeus_command(self):
        process_name = self.get_threshold_var(
            key='process_name',
            default=DEFAULT_PROCESS_NAME,
            value_type='str',
        )

        command = COMMAND.format(process_name=process_name)

        result = self._run_paramiko_commands(
            [{'command': command, 'timeout': self.COMMAND_TIMEOUT}],
            become=True,
            profile='linux',
        )[0]

        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()
        if result.get('rc') != 0:
            return stdout, stderr, self.fail(
                '점검 명령 실행 실패',
                message='JEUS 점검 명령 실행에 실패했습니다.',
                stdout=stdout,
                stderr=stderr,
            )
        return stdout, stderr, None

    def _parse_top_rows(self, stdout):
        rows = []
        header = []
        for line in stdout.splitlines():
            parts = line.split()
            if 'PID' in parts and '%CPU' in parts and '%MEM' in parts:
                header = parts
                continue
            if not header or len(parts) < len(header):
                continue
            try:
                rows.append({
                    'pid': parts[header.index('PID')],
                    'user': parts[header.index('USER')],
                    'state': parts[header.index('S')],
                    'cpu_percent': float(parts[header.index('%CPU')]),
                    'mem_percent': float(parts[header.index('%MEM')]),
                    'command': parts[header.index('COMMAND')],
                })
            except (ValueError, IndexError):
                continue
        return rows

    def run(self):
        stdout, _stderr, error = self._run_jeus_command()
        bad_states = self.get_threshold_var(key='bad_states', default='Z,D,T', value_type='str')
        bad_states = {
            x.strip().upper()
            for x in re.split(r'[|,]+', bad_states)
            if x.strip()
        }        

        if error:
            return error

        rows = self._parse_top_rows(stdout)

        if not rows:
            return self.fail('프로세스 정보 없음', message='top 출력에서 대상 프로세스를 찾지 못했습니다.', stdout=stdout)
            
        bad_rows = [row for row in rows if (row['state'] or '').upper()[:1] in bad_states]
        metrics = {'process_name': 'exTMS', 'process_count': len(rows), 'states': sorted({row['state'] for row in rows}), 'bad_process_count': len(bad_rows), 'bad_processes': bad_rows, 'processes': rows}
        thresholds = {'bad_process_states': sorted(bad_states)}
        if bad_rows:
            return self.warn(metrics=metrics, thresholds=thresholds, reasons='비정상 프로세스 상태가 발견되었습니다.', message='JEUS 프로세스 상태 경고: 비정상 상태 %s건' % len(bad_rows))
        return self.ok(metrics=metrics, thresholds=thresholds, reasons='대상 프로세스 상태에 Z/D/T 상태가 없습니다.', message='JEUS 프로세스 상태 정상: 상태=%s' % ','.join(metrics['states']))


CHECK_CLASS = Check
