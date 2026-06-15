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


DB-OR-SOL-020

# is_required

권고

# inspection_name

온라인 백업 가능 여부 점검

# inspection_content

DB 운영 중 온라인 백업이 가능하도록 아카이브 모드 상태가 활성화 되었는지 점검

# inspection_command

```bash
sqlplus -S /nolog <<EOF
connect / as sysdba
set feedback off
select log_mode from v\$database;
exit;
EOF
```

# inspection_output

```text

```

# description

- 로그 모드가 NOARCHIVELOG로 표시된다면, 데이터베이스의 안정적인 온라인 백업을 위해 ARCHIVELOG 모드로 전환 필요. 전환을 위해 데이터베이스를 재시작하고 ARCHIVELOG 모드를 활성화해야 하며, 이는 즉각적인 조치 권고

- **양호**: 출력값의 LOG_MODE가 'ARCHIVELOG'인 상태
- **경고**: 출력값의 LOG_MODE가 'ARCHIVELOG'가 아닌 상태
- **확인 필요**: 명령어 수행 실패 또는 출력 결과를 확인할 수 없는 경우

# thresholds

[
    {id: null, key: "oracle_account", value: "oracle", sortOrder: 0}
]

# inspection_script

# -*- coding: utf-8 -*-

from .common._base import BaseCheck


LOG_MODE_COMMAND = """sqlplus -S /nolog <<EOF
connect / as sysdba
set feedback off
select log_mode from v\$database;
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
                [{'command': LOG_MODE_COMMAND, 'timeout': 30}],
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
            return self.fail('LOG_MODE SQL 실행 실패', message='v$database log_mode SQL을 실행하지 못했습니다.', stdout=stdout, stderr=stderr)

        modes = [line.strip() for line in stdout.splitlines() if line.strip() in ('ARCHIVELOG', 'NOARCHIVELOG')]
        if not modes:
            return self.fail('LOG_MODE 출력 파싱 실패', message='SQLPlus 출력에서 ARCHIVELOG/NOARCHIVELOG 값을 찾지 못했습니다.', stdout=stdout, stderr=stderr)
        metrics = {
            'oracle_account': oracle_account,
            'verified_oracle_account': switch.get('actual_user') or '',
            'log_mode': modes[-1],
        }
        thresholds = {'oracle_account': oracle_account}
        if modes[-1] != 'ARCHIVELOG':
            return self.fail(
                '아카이브 로그 모드 비활성',
                metrics=metrics,
                thresholds=thresholds,
                message='LOG_MODE가 ARCHIVELOG가 아닙니다.',
            )
        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='LOG_MODE가 ARCHIVELOG입니다.',
            message='온라인 백업 가능 여부 점검 정상',
        )


CHECK_CLASS = Check
