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

DBMS-ORACLE-SOLARIS-REPLAY-012

# is_required

필수

# inspection_name

DB 엔진 로그 파일 점검

# inspection_content

DB 엔진에서 발생되는 Internal(DB 엔진 내부 기능) 에러 로그에 대한 점검

# inspection_command

```bash

```

# inspection_output

```text

```

# description

- ORA-01536: space quota exceeded for tablespace 'USERS' - 테이블스페이스의 공간이 초과되면 사용량을 확인하고, 필요 시 공간을 늘리거나 데이터를 삭제해야 함. 
- error: data file is missing - 데이터 파일이 누락되면 해당 파일의 존재를 확인하고, 복구하거나 재생성해야 함. 
- failure: unable to open database - 데이터베이스가 열리지 않으면 상태를 점검하고, 필요시 다시 시작해야 함. 
- warning: potential configuration issue detected - 구성 문제의 경고가 발생하면 파일을 점검하고 필요한 수정을 해야 함. 
- corrupt: data block corrupted (file # 1, block # 12345) - 데이터 블록이 손상되면 관련 블록을 확인하고 복구 작업을 해야 함. 
- deadlock detected while waiting for resource - 데드락이 발생하면 관련 세션을 종료하여 문제를 해결해야 함. 
- timeout: connection attempt timed out - 연결 시도가 시간 초과되면 네트워크를 점검하고 리스너 및 클라이언트 설정을 조정해야 함. 
※ 기본 경로로 나타냈으며, 사용자가 임의로 경로를 변경했을 경우 수정되어야 함.

- **양호**: 출력값에 결과가 나오지 않은 상태
- **경고**: 출력값에 결과가 나온 상태
- **확인 필요**: 로그 파일 및 경로가 존재하지 않는 경우

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


ENGINE_PATTERN = 'ORA-|error|failure|warning|corrupt|internal|deadlock|timeout'
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
            return self.fail('Oracle 계정 전환 실패', message=switch.get('message') or 'Oracle 계정 전환을 확인하지 못했습니다.', stdout=switch.get('stdout') or '', stderr=switch.get('stderr') or '')

        stdout = result.get('stdout', '')
        match = re.search(r"(/[\w./-]+)", stdout)
        db_log_dir = match.group(1) if match else False

        if not db_log_dir:
            return self.fail('alert log 검색 실패', message='alert log 검색 실패')
        
        command = 'egrep -i "%s" %s/alert_*.log | tail -200' % (ENGINE_PATTERN, shlex.quote(db_log_dir))
        
        result = self._run_paramiko_commands(                
            [{'command': command, 'timeout': 20}],
            become=True
        )[0]

        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()
        
        if result.get('rc') not in (0, 1):
            return self.fail('DB 엔진 로그 grep 실행 실패', message='DB 엔진 alert 로그 검색 명령을 실행하지 못했습니다.', stdout=stdout, stderr=stderr)

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
                'DB 엔진 로그 이상 감지',
                metrics=metrics,
                thresholds=thresholds,
                message='DB 엔진 alert 로그에서 이상 패턴 %s건이 확인되었습니다.' % len(lines),
                stdout=stdout,
                stderr=stderr,
            )
        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='DB 엔진 alert 로그에서 이상 패턴이 검출되지 않았습니다.',
            message='DB 엔진 로그 파일 점검 정상',
        )


CHECK_CLASS = Check
