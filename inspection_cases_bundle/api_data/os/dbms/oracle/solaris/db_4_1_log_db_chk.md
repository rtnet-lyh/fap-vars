# type_name

일상점검

# area_name

상태점검

# category_name

dbms

# application_type

oracle

# application

solaris

# inspection_code

DBMS-ORACLE-SOLARIS-REPLAY-009

# is_required

필수

# inspection_name

DB 로그 파일 점검

# inspection_content

에러 코드(기동 및 정지, 테이블스 페이스 부족 에러, 백업 정상 유무, 데이터 파일 손상, Dead Lock 상태) 를 점검

# inspection_command

```bash

```

# inspection_output

```text

```

# description

- ORA-01536: space quota exceeded for tablespace 'USERS' 
- 지정된 테이블스페이스의 공간 할당량이 초과되었음을 나타냄. 'USERS' 테이블스페이스의 사용량이 할당량을 초과했는지 확인함. 테이블스페이스를 확장하거나 불필요한 데이터를 삭제해야 함. 
- ORA-01110: data file 1 is missing
- 데이터 파일이 누락되었음을 나타냄. 해당 데이터 파일이 정상적으로 존재하는지 확인함. 누락된 데이터 파일을 복구하거나 재생성해야 함. 
- ORA-00060: deadlock detected while waiting for resource
- 두 개 이상의 세션이 서로를 기다리는 데드락 상태가 발생했음을 나타냄. 데드락 발생 시 관련 세션의 상태를 확인함. 대기 중인 세션을 종료하여 데드락 문제를 해결해야 함. 
- ORA-01578: ORACLE data block corrupted (file # 1, block # 12345) 
- 특정 데이터 블록이 손상되었음을 나타냄. 손상된 데이터 블록과 관련된 파일 번호를 확인함. 손상된 블록을 복구하기 위한 조치를 취해야 함. 
- RMAN-08136: WARNING: recovery is incomplete
- RMAN 백업 후 복구가 완료되지 않았음을 나타냄. RMAN 로그에서 복구 상태를 확인함. 복구 작업을 재시도하거나 추가적인 조치를 취해야 함.

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
