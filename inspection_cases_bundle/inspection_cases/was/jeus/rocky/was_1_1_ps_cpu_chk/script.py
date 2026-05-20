# -*- coding: utf-8 -*-

from .common._base import BaseCheck


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
        if error:
            return error
        rows = self._parse_top_rows(stdout)
        if not rows:
            return self.fail('프로세스 정보 없음', message='top 출력에서 대상 프로세스를 찾지 못했습니다.', stdout=stdout)
        threshold = self.get_threshold_var('max_cpu_usage_percent', default=80.0, value_type='float')
        max_row = max(rows, key=lambda row: row['cpu_percent'])
        over_rows = [row for row in rows if row['cpu_percent'] > threshold]
        metrics = {'process_name': 'exTMS', 'process_count': len(rows), 'max_cpu_usage_percent': max_row['cpu_percent'], 'max_cpu_pid': max_row['pid'], 'max_cpu_command': max_row['command'], 'over_threshold_count': len(over_rows), 'processes': rows}
        thresholds = {'max_cpu_usage_percent': threshold}
        if over_rows:
            return self.warn(metrics=metrics, thresholds=thresholds, reasons='CPU 사용률 기준 초과 프로세스가 있습니다.', message='JEUS 프로세스 CPU 사용률 경고: 최대 %.1f%%, 기준 %.1f%%' % (max_row['cpu_percent'], threshold))
        return self.ok(metrics=metrics, thresholds=thresholds, reasons='대상 프로세스 CPU 사용률이 기준 이하입니다.', message='JEUS 프로세스 CPU 사용률 정상: 최대 %.1f%%, 기준 %.1f%%' % (max_row['cpu_percent'], threshold))


CHECK_CLASS = Check
