# type_name

일상점검

# area_name

dbms

# category_name

상태점검

# application_type

oracle

# application

solaris

# inspection_code


DB-OR-SOL-011

# is_required

필수

# inspection_name

Dump파일 생성 여부 확인(DB 오류 발생시 생성)

# inspection_content

DB가 문제 발생시 생성되는 trace(dump)파일로 원인 분석에 주로 사용되며 원인 파일을 위한 파일 점검

# inspection_command

```bash

```

# inspection_output

```text

```

# description

- 이 출력으로 덤프 파일이 생성되었는지 확인할 수 있으며, 파일이 여러 개일 경우 가장 최근 파일을 기준으로 분석을 시작할 수 있음
※ 가장 최근 생성된 trace(.trc) 파일을 확인하여 최근 오류 또는 dump 발새 ㅇ여부를 점검함
- trace 파일이 존재할 경우 최근 생성 시각 및 파일명을 기준으로 분석 수행 가능

# thresholds

[
    {id: null, key: "oracle_account", value: "oratips", sortOrder: 0}
,
{id: null, key: "db_log_dir", value: "/TTIPS_LOG01/diag/rdbms/ttips/TTIPS1/trace", sortOrder: 1}
]

# inspection_script

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
