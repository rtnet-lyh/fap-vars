# -*- coding: utf-8 -*-

from .common._base import BaseCheck


RMAN_SPFILE_COMMAND = """rman target / <<EOF
LIST BACKUP OF SPFILE;
EXIT;
EOF"""


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'solaris'
    PARAMIKO_REUSE_SESSION = False

    def run(self):
        oracle_account = self.get_threshold_var('oracle_account', default='oratips', value_type='str')
        reference_date = self.get_threshold_var('backup_reference_date', default='21-MAY-26', value_type='str')
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

        match_count = stdout.upper().count(str(reference_date or '').upper())
        metrics = {
            'oracle_account': oracle_account,
            'verified_oracle_account': switch.get('actual_user') or '',
            'backup_reference_date_match_count': match_count,
        }
        thresholds = {
            'oracle_account': oracle_account,
            'backup_reference_date': reference_date,
        }
        if not reference_date or match_count < 1:
            return self.fail(
                'SPFILE 백업 기준 날짜 미확인',
                metrics=metrics,
                thresholds=thresholds,
                message='RMAN SPFILE 백업 출력에서 기준 날짜 문자열을 찾지 못했습니다.',
                stdout=stdout,
                stderr=stderr,
            )
        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='RMAN SPFILE 백업 출력에 기준 날짜 문자열이 있습니다.',
            message='환경 설정 파일 백업 점검 정상',
        )


CHECK_CLASS = Check
