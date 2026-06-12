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

DBMS-ORACLE-SOLARIS-REPLAY-022

# is_required

필수

# inspection_name

트랜잭션(데이터베이스 논리적 상태 변경) 로그 사이즈 점검

# inspection_content

DB 운영 시 발생 되는 트랜잭션 로그에 대해 무한정 늘어나는 경우를 대비하여 로그 사이즈 점검, 저장 공간 Full 로 인한 서비스 불가 발생에 따름

# inspection_command

```bash
sqlplus -S /nolog <<EOF
connect / as sysdba
set feedback off
select GROUP#, MEMBERS, BYTES/1024/1024 AS SIZE_MB, STATUS
from V\$log;
exit;
EOF
```

# inspection_output

```text

```

# description

- SIZE_MB: Redo 로그 파일의 크기를 MB 단위로 나타냄. 로그 파일 크기가 적절하지 않을 경우, 성능 문제를 방지하기 위해 크기를 재조정하거나 추가 로그 파일 생성 권고. 
※ 오라클 환경에서 ‘트랜잭션 로그’와 ‘리두 로그’는 같은 개념을 의미함. 
※ 트랜잭션 로그가 무한정 커지지 않도록, 각 로그 파일의 크기와 사용 상태를 주기적으로 점검하여 적절하게 관리해야 함. 
※ 보통 오라클 데이터베이스에서는 각 트랜잭션 로그 그룹에 속한 로그 파일의 크기를 동일하게 설정하는 것이 권장되지만, 반드시 동일할 필요는 없음. 트랜잭션 파일의 크기는 시스템의 설정에 따라 다를 수 있음.

- **양호**: 출력값의 MEMBERS값이 2 이상이며, STATUS값이 'INACTIVE', 'ACTIVE', 'CURRENT'이고, SIZE_MB 값이 최소크기(`min_logfile_size`) 이상인 상태
- **경고**: 출력값의 MEMBERS값이 2 미만이거나,  STATUS값이 'INVALID', 'STALE' 등이며, SIZE_MB 값이 최소크기(`min_logfile_size`) 미만인 상태
- **확인 필요**: 명령어 수행 실패 또는 출력 결과를 확인할 수 없는 경우

# thresholds

[
    {id: null, key: "oracle_account", value: "oratips", sortOrder: 0}
,
{id: null, key: "min_logfile_size", value: "1024", sortOrder: 1}
]

# inspection_script

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
