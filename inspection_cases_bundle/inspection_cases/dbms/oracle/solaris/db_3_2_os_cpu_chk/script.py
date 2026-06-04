# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


CPU_COMMAND = 'ps -eo pid,comm,pcpu | grep ora_'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'solaris'
    PARAMIKO_REUSE_SESSION = False

    def _parse_rows(self, text):
        rows = []
        for line in str(text or '').splitlines():
            parts = re.split(r'\s+', line.strip())
            if len(parts) < 3 or not parts[1].startswith('ora_'):
                continue
            try:
                rows.append({
                    'pid': int(parts[0]),
                    'command': parts[1],
                    'cpu_percent': float(parts[-1]),
                })
            except ValueError:
                continue
        return rows

    def run(self):
        oracle_account = self.get_threshold_var('oracle_account', default='oratips', value_type='str')
        max_cpu_usage_percent = self.get_threshold_var('max_cpu_usage_percent', default=80, value_type='float')
        try:
            result = self._run_solaris_account_commands(
                oracle_account,
                [{'command': CPU_COMMAND, 'timeout': 10}],
            )[0]
        except ValueError as exc:
            return self.fail('Oracle 계정 전환 설정 오류', message=str(exc))

        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()
        switch = getattr(self, '_solaris_last_account_switch_verification', {}) or {}
        if self._is_connection_error(result.get('rc'), stderr):
            return self.fail('호스트 연결 실패', message=stderr or 'Paramiko 연결 확인에 실패했습니다.', stderr=stderr)
        if not switch.get('ok'):
            return self.fail('Oracle 계정 전환 실패', message=switch.get('message') or 'Oracle 계정 전환을 확인하지 못했습니다.', stdout=switch.get('stdout') or '', stderr=stderr)
        if result.get('rc') not in (0, 1):
            return self.fail('ps 명령 실행 실패', message='Oracle 프로세스 CPU 정보를 확인하지 못했습니다.', stdout=stdout, stderr=stderr)

        rows = self._parse_rows(stdout)
        if not rows:
            return self.fail('CPU 출력 파싱 실패', message='ps 출력에서 Oracle CPU 사용 행을 해석하지 못했습니다.', stdout=stdout, stderr=stderr)

        max_row = max(rows, key=lambda row: row['cpu_percent'])
        over_rows = [row for row in rows if row['cpu_percent'] > max_cpu_usage_percent]
        metrics = {
            'oracle_account': oracle_account,
            'verified_oracle_account': switch.get('actual_user') or '',
            'process_count': len(rows),
            'max_cpu_percent': max_row['cpu_percent'],
            'max_cpu_process': max_row['command'],
            'over_threshold_count': len(over_rows),
            'over_threshold_processes': over_rows,
        }
        thresholds = {
            'oracle_account': oracle_account,
            'max_cpu_usage_percent': max_cpu_usage_percent,
        }
        if over_rows:
            return self.fail(
                'Oracle 프로세스 CPU 사용률 임계치 초과',
                metrics=metrics,
                thresholds=thresholds,
                reasons='기준을 초과한 Oracle 프로세스가 있습니다.',
                message='Oracle 프로세스 CPU 최대 사용률 %.2f%%가 기준 %.2f%%를 초과했습니다.' % (max_row['cpu_percent'], max_cpu_usage_percent),
            )
        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='Oracle 프로세스 CPU 사용률이 기준 이하입니다.',
            message='Oracle 프로세스 CPU 최대 사용률 정상: %.2f%%, 기준 %.2f%%' % (max_row['cpu_percent'], max_cpu_usage_percent),
        )


CHECK_CLASS = Check
