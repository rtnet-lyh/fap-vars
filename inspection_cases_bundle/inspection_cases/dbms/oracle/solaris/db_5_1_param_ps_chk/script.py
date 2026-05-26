# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


PROCESS_SQL_COMMAND = """sqlplus -S / as sysdba << EOF
set linesize 200 pagesize 100 feedback off

SELECT
    TO_NUMBER(value) AS "Max Processes",
    (SELECT COUNT(*) FROM v\$session) AS "Current Sessions",
    ROUND(((SELECT COUNT(*) FROM v\$session) / TO_NUMBER(value)) * 100, 2) AS "Usage Percentage"
FROM    v\$parameter
WHERE
    name = 'processes';
EXIT;
EOF"""


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'solaris'
    PARAMIKO_REUSE_SESSION = False

    def _parse_process_row(self, text):
        for line in str(text or '').splitlines():
            match = re.match(r'^\s*(\d+)\s+(\d+)\s+(\d+(?:\.\d+)?)\s*$', line)
            if match:
                return {
                    'max_processes': int(match.group(1)),
                    'current_sessions': int(match.group(2)),
                    'usage_percentage': float(match.group(3)),
                }
        return None

    def run(self):
        oracle_account = self.get_threshold_var('oracle_account', default='oratips', value_type='str')
        max_process_count = self.get_threshold_var('max_process_count', default=100, value_type='int')
        max_current_sessions = self.get_threshold_var('max_current_sessions', default=9000, value_type='int')
        max_usage_percentage = self.get_threshold_var('max_usage_percentage', default=90, value_type='float')
        try:
            result = self._run_solaris_account_commands(
                oracle_account,
                [{'command': PROCESS_SQL_COMMAND, 'timeout': 30}],
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
            return self.fail('프로세스 파라미터 SQL 실행 실패', message='processes 파라미터 SQL을 실행하지 못했습니다.', stdout=stdout, stderr=stderr)

        row = self._parse_process_row(stdout)
        if not row:
            return self.fail('프로세스 파라미터 출력 파싱 실패', message='SQLPlus 출력에서 프로세스 개수 행을 해석하지 못했습니다.', stdout=stdout, stderr=stderr)

        metrics = {
            'oracle_account': oracle_account,
            'verified_oracle_account': switch.get('actual_user') or '',
        }
        metrics.update(row)
        thresholds = {
            'oracle_account': oracle_account,
            'max_process_count': max_process_count,
            'max_current_sessions': max_current_sessions,
            'max_usage_percentage': max_usage_percentage,
        }
        reasons = []
        if row['max_processes'] < max_process_count:
            reasons.append('Max Processes 값이 최소 기준 %s보다 작습니다.' % max_process_count)
        if row['current_sessions'] > max_current_sessions:
            reasons.append('Current Sessions 값이 기준 %s를 초과했습니다.' % max_current_sessions)
        if row['usage_percentage'] > max_usage_percentage:
            reasons.append('Usage Percentage 값이 기준 %.2f%%를 초과했습니다.' % max_usage_percentage)
        if reasons:
            return self.fail(
                '프로세스 파라미터 기준 미달',
                metrics=metrics,
                thresholds=thresholds,
                reasons=reasons,
                message='Oracle processes 파라미터 점검 기준을 만족하지 못했습니다.',
            )
        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='프로세스 최대값, 현재 세션 수, 사용률이 기준을 만족합니다.',
            message='Oracle processes 파라미터 점검 정상',
        )


CHECK_CLASS = Check
