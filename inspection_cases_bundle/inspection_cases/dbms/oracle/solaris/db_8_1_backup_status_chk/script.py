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
