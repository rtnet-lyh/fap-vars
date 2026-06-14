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

DBMS-ORACLE-SOLARIS-REPLAY-017

# is_required

권고

# inspection_name

리두로그 파일(데이터 변경사항 파일) 이중화

# inspection_content

데이터 변경 사항을 기록하는 오라클 온라인 리두로그 파일로 파일 손상에 대비하여 2개 이상의 이중화(물리적, 논리적) 파일로 구성되어 있는지 점검

# inspection_command

```bash
sqlplus -S /nolog <<EOF
CONNECT / AS SYSDBA
set linesize 200 pagesize 100 feedback off
col member format a40
col status format a10
col type format a10
SELECT * FROM V\$logfile;
EXIT;
EOF
```

# inspection_output

```text

```

# description

- STATUS: 로그 파일의 현재 상태를 나타내며, 주로 "ONLINE" 상태로 표시됨. 이는 로그 파일이 정상적으로 운영 중임을 의미함. 모든 로그 파일이 "ONLINE" 상태여야 하며, 상태가 "INVALID" 또는 "STALE"로 표시될 경우, 해당 로그 파일을 복구하거나 교체하는 것이 권고. 
- TYPE: Redo Log 파일 상태 정보
- MEMBER: Redo Log 파일 경로 정보

※ 부연설명
- Oracle 버전에 따라 v$logfile의 STATUS 컬럼 값이 공백(NULL)으로 표시될 수 있음
- TYPE 값이 ONLINE인 경우 정상 운영 상태로 판단
- 동일 GROUP# 내 MEMBER가 2개 이상이며 서로 다른 디스크 또는 마운트 포인트에 구성되어 있는지 확인 필요
- Redo Log 파일은 장애 복구에 중요한 정보이므로 물리적으로 다른 경로에 두고 이중화 구성 권고

- **양호**: 동일 GROUP# 내 MEMBER가 2개 이상이며, 서로 다른 디스크 또는 마운트 포인트에 분산 구성된 경우
- **경고**: TYPE값이 ONLINE이 아니거나 동일 GROUP# 내 MEMBER가 1개만 존재하는 경우
- **확인 필요**: 명령어 수행 실패 또는 출력 결과를 확인할 수 없는 경우

# thresholds

[
    {id: null, key: "oracle_account", value: "oratips", sortOrder: 0}
,
{id: null, key: "redo_group_member_count", value: "2", sortOrder: 1}
]

# inspection_script

# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


LOGFILE_COMMAND = """sqlplus -S /nolog <<EOF
CONNECT / AS SYSDBA
set linesize 200 pagesize 100 feedback off
col member format a40
col status format a10
col type format a10
SELECT * FROM V\$logfile;
EXIT;
EOF"""


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'solaris'
    PARAMIKO_REUSE_SESSION = False

    def _mount(self, path):
        parts = str(path or '').split('/')
        return '/' + parts[1] if len(parts) > 1 and parts[1] else '/'

    def _parse_members(self, text):
        rows = []
        for line in str(text or '').splitlines():
            parts = re.split(r'\s+', line.strip())
            if len(parts) < 4 or not parts[0].isdigit():
                continue
            path_index = next((index for index, part in enumerate(parts) if part.startswith('/')), None)
            if path_index is None or path_index < 2:
                continue
            before_path = parts[1:path_index]
            rows.append({
                'group': int(parts[0]),
                'status': before_path[-2] if len(before_path) > 1 else '',
                'type': before_path[-1],
                'member': parts[path_index],
                'mount_point': self._mount(parts[path_index]),
            })
        return rows

    def run(self):
        oracle_account = self.get_threshold_var('oracle_account', default='oratips', value_type='str')
        redo_group_member_count = self.get_threshold_var('redo_group_member_count', default=2, value_type='int')
        try:
            result = self._run_solaris_account_commands(
                oracle_account,
                [{'command': LOGFILE_COMMAND, 'timeout': 30}],
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
            return self.fail('redo logfile SQL 실행 실패', message='redo logfile 이중화 SQL을 실행하지 못했습니다.', stdout=stdout, stderr=stderr)

        rows = self._parse_members(stdout)
        if not rows:
            return self.fail('redo logfile 출력 파싱 실패', message='SQLPlus 출력에서 redo logfile MEMBER 행을 찾지 못했습니다.', stdout=stdout, stderr=stderr)
        groups = {}
        invalid_rows = []
        for row in rows:
            groups.setdefault(row['group'], []).append(row)
            if row['type'] != 'ONLINE':
                invalid_rows.append(row)
        group_metrics = []
        failed_groups = []
        for group, members in sorted(groups.items()):
            mounts = sorted(set(member['mount_point'] for member in members))
            group_metrics.append({
                'group': group,
                'member_count': len(members),
                'mount_points': mounts,
                'members': [member['member'] for member in members],
            })
            if len(members) < redo_group_member_count or len(mounts) < redo_group_member_count:
                failed_groups.append(group)
        metrics = {
            'oracle_account': oracle_account,
            'verified_oracle_account': switch.get('actual_user') or '',
            'redo_group_count': len(group_metrics),
            'redo_groups': group_metrics,
            'invalid_type_count': len(invalid_rows),
            'failed_groups': failed_groups,
        }
        thresholds = {
            'oracle_account': oracle_account,
            'redo_group_member_count': redo_group_member_count,
        }
        if invalid_rows or failed_groups:
            return self.fail(
                'redo logfile 이중화 기준 미달',
                metrics=metrics,
                thresholds=thresholds,
                message='ONLINE이 아닌 redo member가 있거나 그룹별 member/mount 분산 수가 기준보다 작습니다.',
            )
        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='redo 그룹별 member 수와 마운트 포인트 분산이 기준을 만족합니다.',
            message='redo logfile 이중화 점검 정상',
        )


CHECK_CLASS = Check
