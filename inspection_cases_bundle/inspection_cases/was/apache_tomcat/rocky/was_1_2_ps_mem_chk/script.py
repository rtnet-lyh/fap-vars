# -*- coding: utf-8 -*-

from .common._base import BaseCheck


COMMAND = 'ps -eo pid,comm,%mem,rss --sort=-%mem'
COMMAND_TIMEOUT = 20
TOP_PROCESS_LIMIT = 10


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
                message='Apache Tomcat 메모리 사용률 점검 명령 실행에 실패했습니다.',
                stdout=stdout,
                stderr=stderr,
            )
        return stdout, stderr, None

    def _parse_rows(self, stdout):
        rows = []
        header_found = False
        for line in stdout.splitlines():
            parts = line.strip().split()
            if not parts:
                continue
            if 'PID' in parts and 'COMMAND' in parts and '%MEM' in parts and 'RSS' in parts:
                header_found = True
                continue
            if not header_found or len(parts) < 4:
                continue
            try:
                pid = int(parts[0])
                mem_percent = float(parts[-2])
                rss_kib = int(parts[-1])
            except ValueError:
                continue
            command = ' '.join(parts[1:-2]).strip()
            if command:
                rows.append({
                    'pid': pid,
                    'command': command,
                    'mem_percent': mem_percent,
                    'rss_kib': rss_kib,
                })
        return rows

    def run(self):
        stdout, _stderr, error = self._run_command()
        if error:
            return error

        threshold = self.get_threshold_var('max_usage_percent', default=80.0, value_type='float')
        thresholds = {'max_usage_percent': threshold}
        rows = self._parse_rows(stdout)
        if not rows:
            return self.fail(
                '메모리 사용률 파싱 실패',
                message='ps 출력에서 프로세스 메모리 사용률 정보를 해석할 수 없습니다.',
                stdout=stdout,
                thresholds=thresholds,
            )

        max_row = max(rows, key=lambda row: row['mem_percent'])
        over_rows = [row for row in rows if row['mem_percent'] > threshold]
        metrics = {
            'process_count': len(rows),
            'max_usage_percent': max_row['mem_percent'],
            'max_usage_pid': max_row['pid'],
            'max_usage_command': max_row['command'],
            'max_usage_rss_kib': max_row['rss_kib'],
            'over_threshold_count': len(over_rows),
            'over_threshold_processes': over_rows,
            'top_processes': rows[:TOP_PROCESS_LIMIT],
        }
        if over_rows:
            return self.warn(
                metrics=metrics,
                thresholds=thresholds,
                reasons='메모리 사용률이 기준을 초과한 프로세스가 있습니다.',
                message='Apache Tomcat 프로세스 메모리 사용률 경고: 최대 %.1f%%, 기준 %.1f%%' % (
                    max_row['mem_percent'],
                    threshold,
                ),
            )
        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='프로세스 메모리 사용률이 기준 이하입니다.',
            message='Apache Tomcat 프로세스 메모리 사용률 정상: 최대 %.1f%%, 기준 %.1f%%' % (
                max_row['mem_percent'],
                threshold,
            ),
        )


CHECK_CLASS = Check
