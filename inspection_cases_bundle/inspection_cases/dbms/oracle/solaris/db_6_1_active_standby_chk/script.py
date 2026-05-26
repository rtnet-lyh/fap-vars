# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


ARCHIVE_DEST_COMMAND = """sqlplus -S / as sysdba <<EOF
ALTER SESSION SET NLS_LANGUAGE = 'AMERICAN';
set pagesize 100 linesize 300 feedback off heading on;
col destination format a40
col error format a30 

SELECT destination, status, error 
FROM v\$archive_dest 
WHERE destination IS NOT NULL;
exit
EOF"""


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'solaris'
    PARAMIKO_REUSE_SESSION = False

    def _parse_destinations(self, text):
        rows = []
        for line in str(text or '').splitlines():
            match = re.match(r'^\s*(/\S+)\s+([A-Z]+)(?:\s+(.*))?$', line)
            if match:
                rows.append({
                    'destination': match.group(1),
                    'status': match.group(2),
                    'error': (match.group(3) or '').strip(),
                })
        return rows

    def run(self):
        oracle_account = self.get_threshold_var('oracle_account', default='oratips', value_type='str')
        try:
            result = self._run_solaris_account_commands(
                oracle_account,
                [{'command': ARCHIVE_DEST_COMMAND, 'timeout': 30}],
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
            return self.fail('archive destination SQL 실행 실패', message='archive destination 상태 SQL을 실행하지 못했습니다.', stdout=stdout, stderr=stderr)

        rows = self._parse_destinations(stdout)
        if not rows:
            return self.fail('archive destination 출력 파싱 실패', message='SQLPlus 출력에서 archive destination 상태 행을 찾지 못했습니다.', stdout=stdout, stderr=stderr)
        invalid_rows = [row for row in rows if row['status'] != 'VALID']
        metrics = {
            'oracle_account': oracle_account,
            'verified_oracle_account': switch.get('actual_user') or '',
            'destination_count': len(rows),
            'destinations': rows,
            'invalid_destination_count': len(invalid_rows),
        }
        thresholds = {'oracle_account': oracle_account}
        if invalid_rows:
            return self.fail(
                'archive destination 상태 이상',
                metrics=metrics,
                thresholds=thresholds,
                message='VALID가 아닌 archive destination 상태가 확인되었습니다.',
            )
        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='archive destination STATUS가 모두 VALID입니다.',
            message='Active-Standby archive destination 점검 정상',
        )


CHECK_CLASS = Check
