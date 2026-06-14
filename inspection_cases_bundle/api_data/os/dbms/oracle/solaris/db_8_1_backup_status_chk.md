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

DBMS-ORACLE-SOLARIS-REPLAY-019

# is_required

필수

# inspection_name

DB 백업 상태 점검

# inspection_content

백업 형태(Begin/End, Rman, Exp 등), 날짜, 로그, 파일수 등을 점검하여 장애 시 완전 복구 가능 여부 점검

# inspection_command

```bash
sqlplus -S /nolog <<EOF
rman target / <<EOF
LIST BACKUP SUMMARY;
EXIT;
EOF
```

# inspection_output

```text

```

# description

- Completion Time: 백업이 완료된 시간을 나타내며, 백업이 정기적으로 수행되지 않았다면 백업 스케줄을 재검토하고 수정이 필요. 데이터 손실을 방지하고 최신 데이터를 복구하기 위해서는 주기적으로 백업이 완료되어야 하므로, 백업이 완료된 시간을 확인함으로써 점검할 수 있음.
※ 사용자 정의값인 `backup_threshold_days`일 이내 정상 백업 수행 권고
- (현재 시간 - Completion Time) > `backup_threshold_days` 인 경우 비정상

- **양호**: 현재 시간과 마지막 백업 완료시간(Completion Time) 값이 `backup_threshold_days` 이내인 상태 
- **경고**: 현재 시간과 마지막 백업 완료시간(Completion Time) 값이 `backup_threshold_days` 를 초과한 상태
- **확인 필요**: 명령어 수행 실패 또는 출력 결과를 확인할 수 없는 경우

# thresholds

[
    {id: null, key: "oracle_account", value: "oratips", sortOrder: 0}
,
{id: null, key: "backup_threshold_days", value: "7", sortOrder: 1}
]

# inspection_script

# -*- coding: utf-8 -*-

import datetime
import re

from .common._base import BaseCheck


RMAN_SUMMARY_COMMAND = """rman target / <<EOF
LIST BACKUP SUMMARY;
EXIT;
EOF"""


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'solaris'
    PARAMIKO_REUSE_SESSION = False

    def _parse_dates(self, text):
        dates = []
        for value in re.findall(r'\b\d{2}-[A-Z]{3}-\d{2}\b', str(text or ''), flags=re.I):
            try:
                dates.append((datetime.datetime.strptime(value.upper(), '%d-%b-%y').date(), value.upper()))
            except ValueError:
                continue
        return dates

    def run(self):
        oracle_account = self.get_threshold_var('oracle_account', default='oratips', value_type='str')
        backup_threshold_days = self.get_threshold_var('backup_threshold_days', default=7, value_type='int')
        try:
            result = self._run_solaris_account_commands(
                oracle_account,
                [{'command': RMAN_SUMMARY_COMMAND, 'timeout': 60}],
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
            return self.fail('RMAN 백업 요약 실행 실패', message='RMAN LIST BACKUP SUMMARY를 실행하지 못했습니다.', stdout=stdout, stderr=stderr)

        dates = self._parse_dates(stdout)
        if not dates:
            return self.fail('RMAN 백업 날짜 파싱 실패', message='RMAN 출력에서 Completion Time 날짜를 찾지 못했습니다.', stdout=stdout, stderr=stderr)
        
        latest_date, latest_text = max(dates, key=lambda item: item[0])
        elapsed_days = (datetime.date.today() - latest_date).days
        metrics = {
            'oracle_account': oracle_account,
            'verified_oracle_account': switch.get('actual_user') or '',
            'backup_completion_date_count': len(dates),
            'latest_backup_completion_time': latest_text,
            'days_since_latest_backup': elapsed_days,
        }
        thresholds = {
            'oracle_account': oracle_account,
            'backup_threshold_days': backup_threshold_days,
        }
        if elapsed_days < 0:
            return self.fail(
                'RMAN 백업 날짜 검증 실패',
                metrics=metrics,
                thresholds=thresholds,
                message='마지막 백업 날짜가 점검 실행 날짜보다 미래입니다.',
            )
        if elapsed_days > backup_threshold_days:
            return self.fail(
                'RMAN 백업 완료 시점 기준 초과',
                metrics=metrics,
                thresholds=thresholds,
                message='마지막 백업 완료 시점이 허용 경과 일수를 초과했습니다.',
            )
        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='마지막 RMAN 백업 완료 시점이 허용 경과 일수 이내입니다.',
            message='DB 백업 상태 점검 정상',
        )


CHECK_CLASS = Check
