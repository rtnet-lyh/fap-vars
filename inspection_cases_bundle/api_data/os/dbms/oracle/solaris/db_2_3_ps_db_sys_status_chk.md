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

DBMS-ORACLE-SOLARIS-REPLAY-006

# is_required

필수

# inspection_name

DB 접속 상태 점검

# inspection_content

DB가 기동되어 있으나 실제 이상없이 DB가 접속 가능하는지 점검(SQL 커맨드 모드로 접근하여 명령어 수행 상태 정상 점검)

# inspection_command

```bash
sqlplus -S /nolog << EOF
connect / as sysdba
select 'DB is accessible' from dual;
exit;
EOF
```

# inspection_output

```text

```

# description

- 출력에 'DB is accessible'가 표시되면, DB가 정상적으로 작동 중이며, 접속이 가능하다는 것을 의미함
- 출력에 'DB is accessible' 메시지가 나타나지 않거나, SQL*Plus에서 오류 메시지가 나타난다면, DB 접속에 문제가 있음을 뜻함. DB가 기동되지 않았거나, 네트워크 문제, 권한 문제, 등의 점검이 필요

- **양호**: 출력에 'DB is accessible'가 표시된 상태
- **경고**: 출력에 'DB is accessible' 메시지가 나타나지 않거나, SQL*Plus에서 오류 메시지가 나타난 상태
- **확인 필요**: 대상 프로세스가 없거나 sqlplus 명령을 사용할 수 없는 상태

# thresholds

[
    {id: null, key: "oracle_account", value: "oratips", sortOrder: 0}
]

# inspection_script

# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


SQL_COMMAND = """sqlplus -S /nolog << EOF
connect / as sysdba
select 'DB is accessible' from dual;
exit;
EOF"""


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'solaris'
    PARAMIKO_REUSE_SESSION = False

    def run(self):
        oracle_account = self.get_threshold_var('oracle_account', default='oratips', value_type='str')
        try:
            result = self._run_solaris_account_commands(
                oracle_account,
                [{'command': SQL_COMMAND, 'timeout': 20}],
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
            return self.fail('SQLPlus 명령 실행 실패', message='DB 접속 상태 SQL을 실행하지 못했습니다.', stdout=stdout, stderr=stderr)
        if re.search(r'(^|\s)(?:ORA-|SP2-|TNS-)', stdout + '\n' + stderr, flags=re.MULTILINE):
            return self.fail('DB 접속 오류 출력 감지', message='SQLPlus 출력에서 Oracle 오류 코드가 확인되었습니다.', stdout=stdout, stderr=stderr)

        marker_count = stdout.count('DB is accessible')
        metrics = {
            'oracle_account': oracle_account,
            'verified_oracle_account': switch.get('actual_user') or '',
            'accessible_marker_count': marker_count,
        }
        thresholds = {'oracle_account': oracle_account}
        if marker_count < 1:
            return self.fail(
                'DB 접속 확인 문구 미확인',
                metrics=metrics,
                thresholds=thresholds,
                message="SQLPlus 출력에서 'DB is accessible' 문구를 찾지 못했습니다.",
                stdout=stdout,
                stderr=stderr,
            )
        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons="SQLPlus 출력에 'DB is accessible' 문구가 있습니다.",
            message='Oracle DB 접속 상태 정상',
        )


CHECK_CLASS = Check
