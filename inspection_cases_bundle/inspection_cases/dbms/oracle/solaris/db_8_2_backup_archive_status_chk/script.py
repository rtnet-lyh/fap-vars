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
