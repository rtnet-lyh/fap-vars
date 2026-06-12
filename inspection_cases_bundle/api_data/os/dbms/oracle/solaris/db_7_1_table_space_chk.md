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

DBMS-ORACLE-SOLARIS-REPLAY-018

# is_required

필수

# inspection_name

테이블 스페이스 사용률 점검

# inspection_content

DB 데이터가 저장되는 테이블 스페이스 영역의 사용률이 90% 이상을 사용할 경우 테이블 스페이스 공간 확보 대비

# inspection_command

```bash
sqlplus -S /nolog <<EOF
connect / as sysdba
set feedback off
col usage_percent format 990.99
select tablespace_name, round(used_percent,2) as USAGE_PERCENT
from dba_tablespace_usage_metrics;
exit;
EOF
```

# inspection_output

```text

```

# description

- USAGE_PERCENT: 테이블 스페이스의 사용률을 백분율로 나타내며, 사용률이 과도할 경우 경고 수준. 사용률이 과다하면 공간 부족 가능성이 높아지므로 즉각적인 공간 확보가 필요. 테이블 스페이스 확장이 권고되며, 심각할 경우 공간 확보가 필요.

- **양호**: USAGE_PERCENT 값이 `max_ts_usage_pct` 미만인 경우
- **경고**: USAGE_PERCENT 값이 `max_ts_usage_pct` 이상인 경우
- **확인 필요**: 명령어 수행 실패 또는 출력 결과를 확인할 수 없는 경우

# thresholds

[
    {id: null, key: "oracle_account", value: "oratips", sortOrder: 0}
,
{id: null, key: "max_ts_usage_pct", value: "90", sortOrder: 1}
]

# inspection_script

# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


TABLESPACE_COMMAND = """sqlplus -S /nolog <<EOF
connect / as sysdba
set feedback off
col usage_percent format 990.99
select tablespace_name, round(used_percent,2) as USAGE_PERCENT
from dba_tablespace_usage_metrics;
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
            match = re.match(r'^\s*([A-Z][A-Z0-9_$#]*)\s+(\d+(?:\.\d+)?)\s*$', line)
            if match:
                rows.append({
                    'tablespace_name': match.group(1),
                    'usage_percent': float(match.group(2)),
                })
        return rows

    def run(self):
        oracle_account = self.get_threshold_var('oracle_account', default='oratips', value_type='str')
        max_ts_usage_pct = self.get_threshold_var('max_ts_usage_pct', default=90, value_type='float')
        try:
            result = self._run_solaris_account_commands(
                oracle_account,
                [{'command': TABLESPACE_COMMAND, 'timeout': 30}],
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
            return self.fail('tablespace SQL 실행 실패', message='tablespace 사용률 SQL을 실행하지 못했습니다.', stdout=stdout, stderr=stderr)

        rows = self._parse_rows(stdout)
        if not rows:
            return self.fail('tablespace 출력 파싱 실패', message='SQLPlus 출력에서 tablespace 사용률 행을 찾지 못했습니다.', stdout=stdout, stderr=stderr)
        max_row = max(rows, key=lambda row: row['usage_percent'])
        over_rows = [row for row in rows if row['usage_percent'] >= max_ts_usage_pct]
        metrics = {
            'oracle_account': oracle_account,
            'verified_oracle_account': switch.get('actual_user') or '',
            'tablespace_count': len(rows),
            'max_tablespace_name': max_row['tablespace_name'],
            'max_usage_percent': max_row['usage_percent'],
            'over_threshold_count': len(over_rows),
            'over_threshold_tablespaces': over_rows,
        }
        thresholds = {'oracle_account': oracle_account, 'max_ts_usage_pct': max_ts_usage_pct}
        if over_rows:
            return self.fail(
                'tablespace 사용률 임계치 초과',
                metrics=metrics,
                thresholds=thresholds,
                message='기준 이상인 tablespace 사용률이 확인되었습니다.',
            )
        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='모든 tablespace 사용률이 기준 미만입니다.',
            message='tablespace 사용률 점검 정상',
        )


CHECK_CLASS = Check
