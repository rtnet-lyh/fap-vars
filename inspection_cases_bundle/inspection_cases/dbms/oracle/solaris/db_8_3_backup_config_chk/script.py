# -*- coding: utf-8 -*-

from .common._base import BaseCheck
import re
from datetime import datetime, date

RMAN_SPFILE_COMMAND = '''rman target / <<EOF
LIST BACKUP OF SPFILE;
EXIT;
EOF'''


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'solaris'
    PARAMIKO_REUSE_SESSION = False

    def _parse_completion_time(self, output, threshold_days=30):
        results = {
            "is_pass": False,
            "latest_completion_time": None,
            "elapsed_days": None,
            "threshold_days": threshold_days,
            "message": ""
        }

        date_matches = re.findall(
            r"\d{2}:\d{2}:\d{2}\s+(\d{2}-[A-Z]+-\d{2})",
            output.upper()
        )   

        if not date_matches:
            results["message"] = "Completion Time 정보를 찾지 못했습니다."

        else:
            completion_dates = [                
                datetime.strptime(d, "%d-%b-%y").date()
                for d in date_matches
            ]
        
            oldest_date = min(completion_dates)

            elapsed_days = (date.today() - oldest_date).days

            results.update({
                "is_pass": elapsed_days <= threshold_days,
                "oldes_completion_time": oldest_date.strftime("%Y-%m-%d"),
                "elapsed_days": elapsed_days,
                "message":(
                    "정상"
                    if elapsed_days <= threshold_days
                    else f"{threshold_days}일 이상 경과"
                )
            })

        return results

    def run(self):
        pasred = {}
        oracle_account = self.get_threshold_var('oracle_account', default='oratips', value_type='str')
        threshold_days = self.get_threshold_var('threshold_days', default=30, value_type='int')
        try:
            result = self._run_solaris_account_commands(
                oracle_account,
                [{'command': RMAN_SPFILE_COMMAND, 'timeout': 60}],
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
            return self.fail('RMAN SPFILE 백업 조회 실패', message='RMAN LIST BACKUP OF SPFILE을 실행하지 못했습니다.', stdout=stdout, stderr=stderr)

        pasred = self._parse_completion_time(stdout, threshold_days)
        
        metrics = {
            'oracle_account': oracle_account,
            'verified_oracle_account': switch.get('actual_user') or '',
            'backup_threshold_days_result': pasred,
        }
        thresholds = {
            'oracle_account': oracle_account,
            'threshold_days': threshold_days,
        }
        if not pasred.get("is_pass"):
            return self.fail(
                'SPFILE 백업 기준 날짜 미확인',
                metrics=metrics,
                thresholds=thresholds,
                message=f'가장 오래된 백업날짜가 {threshold_days}을 초과 했습니다.',
                stdout=stdout,
                stderr=stderr,
            )
        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons=f'가장 오래된 백업날짜가 {threshold_days}일 내에 있습니다.',
            message=f'가장 오래된 백업날짜가 {threshold_days}일 내에 있습니다.',
        )

CHECK_CLASS = Check