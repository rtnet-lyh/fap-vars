# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


LOG_SIZE_COMMAND = """sqlplus -S /nolog <<EOF
connect / as sysdba
set feedback off
select GROUP#, MEMBERS, BYTES/1024/1024 AS SIZE_MB, STATUS
from V\$log;
exit;
EOF"""


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'solaris'
    PARAMIKO_REUSE_SESSION = False

    def _parse_rows(self, text):
        rows = []
        for line in str(text or '').splitlines():
            match = re.match(r'^\s*(\d+)\s+(\d+)\s+(\d+(?:\.\d+)?)\s+([A-Z]+)\s*$', line)
            if match:
                rows.append({
                    'group': int(match.group(1)),
                    'members': int(match.group(2)),
                    'size_mb': float(match.group(3)),
                    'status': match.group(4),
                })
        return rows

    def run(self):
        oracle_account = self.get_threshold_var('oracle_account', default='oratips', value_type='str')
        min_logfile_size = self.get_threshold_var('min_logfile_size', default=1024, value_type='float')
        try:
            result = self._run_solaris_account_commands(
                oracle_account,
                [{'command': LOG_SIZE_COMMAND, 'timeout': 30}],
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
        if result.get('rc') != 0:
            return self.fail('redo log 크기 SQL 실행 실패', message='V$log 트랜잭션 로그 크기 SQL을 실행하지 못했습니다.', stdout=stdout, stderr=stderr)

        rows = self._parse_rows(stdout)
        if not rows:
            return self.fail('redo log 크기 출력 파싱 실패', message='SQLPlus 출력에서 redo log 크기 행을 찾지 못했습니다.', stdout=stdout, stderr=stderr)
        allowed_status = {'INACTIVE', 'ACTIVE', 'CURRENT'}
        failed_rows = [
            row for row in rows
            if row['members'] < 2 or row['size_mb'] < min_logfile_size or row['status'] not in allowed_status
        ]
        metrics = {
            'oracle_account': oracle_account,
            'verified_oracle_account': switch.get('actual_user') or '',
            'log_group_count': len(rows),
            'failed_group_count': len(failed_rows),
            'log_groups': rows,
        }
        thresholds = {'oracle_account': oracle_account, 'min_logfile_size': min_logfile_size}
        if failed_rows:
            return self.fail(
                '트랜잭션 로그 기준 미달',
                metrics=metrics,
                thresholds=thresholds,
                message='redo log member 수, 상태, 또는 크기가 기준을 만족하지 못합니다.',
            )
        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='redo log member 수, 상태, 크기가 기준을 만족합니다.',
            message='트랜잭션 로그 사이즈 점검 정상',
        )


CHECK_CLASS = Check
