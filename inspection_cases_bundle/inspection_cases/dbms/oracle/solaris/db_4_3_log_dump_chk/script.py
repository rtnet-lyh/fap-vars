# -*- coding: utf-8 -*-

import shlex
import re

from .common._base import BaseCheck

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

        command = 'cd %s && ls -ltr *.trc | tail -1' % shlex.quote(db_log_dir)
        
        result = self._run_paramiko_commands(            
            [{'command': command, 'timeout': 20}],
            become=True
        )[0]        

        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()
        
        if result.get('rc') != 0:
            return self.fail('trace 파일 조회 실패', message='trace 파일 디렉터리에서 최근 dump 파일을 조회하지 못했습니다.', stdout=stdout, stderr=stderr)

        lines = [line for line in stdout.splitlines() if line.strip()]
        metrics = {
            'oracle_account': oracle_account,
            'verified_oracle_account': switch.get('actual_user') or '',
            'trace_file_count': len(lines),
            'latest_trace_file_line': lines[-1] if lines else '',
        }
        thresholds = {'oracle_account': oracle_account, 'db_log_dir': db_log_dir}
        if lines:
            return self.warn(
                metrics=metrics,
                thresholds=thresholds,
                message='최근 trace dump 파일이 확인되어 수동 분석이 필요합니다.',
                reasons='최근 trace dump 파일이 확인되어 수동 분석이 필요합니다.',                
            )
        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='최근 trace dump 파일 출력이 없습니다.',
            message='trace dump 파일 생성 여부 점검 정상',
        )


CHECK_CLASS = Check
