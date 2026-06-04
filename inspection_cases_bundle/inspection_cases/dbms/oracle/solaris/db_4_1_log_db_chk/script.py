# -*- coding: utf-8 -*-

import shlex
import re

from .common._base import BaseCheck


LOG_PATTERN = 'ORA-01536|ORA-01110|ORA-00060|ORA-01578|RMAN-08136'
DIAG_TRACE_PATH_QUERY = """sqlplus -S / as sysdba << EOF
set pages 0 feedback off heading off
SELECT value
FROM v\$diag_info where name = 'Diag Trace';
EXIT;
EOF"""

class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'solaris'
    PARAMIKO_REUSE_SESSION = False

    def run(self):
        oracle_account = self.get_threshold_var('oracle_account', default='oratips', value_type='str')

        # log 경로를 찾기위한 쿼리 실행
        try:
            result = self._run_solaris_account_commands(
                oracle_account,
                [{'command': DIAG_TRACE_PATH_QUERY, 'timeout': 20}],
            )[0]
        except ValueError as exc:
            return self.fail('Oracle 계정 전환 설정 오류', message=str(exc))

        switch = getattr(self, '_solaris_last_account_switch_verification', {}) or {}
        if not switch.get('ok'):
            return self.fail('Oracle 계정 전환 실패', message=switch.get('message') or 'Oracle 계정 전환을 확인하지 못했습니다.', stdout=switch.get('stdout') or '', stderr=stderr)

        stdout = result.get('stdout', '')
        match = re.search(r"(/[\w./-]+)", stdout)
        db_log_dir = match.group(1) if match else False

        if not db_log_dir:
            return self.fail('alert log 검색 실패', message='alert log 검색 실패')
        
        # 로그 확인
        command = "egrep -i '%s' %s/alert_*.log" % (LOG_PATTERN, shlex.quote(db_log_dir))
    
        result = self._run_paramiko_commands(                
            [{'command': command, 'timeout': 20}],
            become=True
        )[0]

        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()
        
        if result.get('rc') not in (0, 1):
            return self.fail('DB 로그 grep 실행 실패', message='DB 로그 파일에서 Oracle 오류 번호를 검색하지 못했습니다.', stdout=stdout, stderr=stderr)

        lines = [line for line in stdout.splitlines() if line.strip()]
        metrics = {
            'oracle_account': oracle_account,
            'verified_oracle_account': switch.get('actual_user') or '',
            'matched_log_count': len(lines),
            'matched_logs': lines,
        }
        thresholds = {'oracle_account': oracle_account, 'db_log_dir': db_log_dir}
        if lines:
            return self.fail(
                'DB 로그 오류 번호 감지',
                metrics=metrics,
                thresholds=thresholds,
                message='DB alert 로그에서 점검 대상 오류 번호 %s건이 확인되었습니다.' % len(lines),
                stdout=stdout,
                stderr=stderr,
            )
        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='DB alert 로그에서 점검 대상 오류 번호가 검출되지 않았습니다.',
            message='DB 로그 파일 점검 정상',
        )


CHECK_CLASS = Check
