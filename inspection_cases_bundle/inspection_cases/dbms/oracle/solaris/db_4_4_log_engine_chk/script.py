# -*- coding: utf-8 -*-

import shlex

from .common._base import BaseCheck


ENGINE_PATTERN = 'ORA-|error|failure|warning|corrupt|internal|deadlock|timeout'
DEFAULT_DB_LOG_DIR = '/TTIPS_LOG01/diag/rdbms/ttips/TTIPS1/trace'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'solaris'
    PARAMIKO_REUSE_SESSION = False

    def run(self):
        oracle_account = self.get_threshold_var('oracle_account', default='oratips', value_type='str')
        db_log_dir = self.get_threshold_var('db_log_dir', default=DEFAULT_DB_LOG_DIR, value_type='str')
        command = 'egrep -i "%s" %s/alert_*.log' % (ENGINE_PATTERN, shlex.quote(db_log_dir))
        try:
            result = self._run_solaris_account_commands(
                oracle_account,
                [{'command': command, 'timeout': 20}],
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
        if result.get('rc') not in (0, 1):
            return self.fail('DB 엔진 로그 grep 실행 실패', message='DB 엔진 alert 로그 검색 명령을 실행하지 못했습니다.', stdout=stdout, stderr=stderr)

        lines = [line for line in stdout.splitlines() if line.strip()]
        metrics = {
            'oracle_account': oracle_account,
            'verified_oracle_account': switch.get('actual_user') or '',
            'matched_log_count': len(lines),
            'matched_logs': lines,
        }
        thresholds = {'oracle_account': oracle_account, 'db_log_dir': db_log_dir}
        if lines:
            return self.fail(
                'DB 엔진 로그 이상 감지',
                metrics=metrics,
                thresholds=thresholds,
                message='DB 엔진 alert 로그에서 이상 패턴 %s건이 확인되었습니다.' % len(lines),
                stdout=stdout,
                stderr=stderr,
            )
        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='DB 엔진 alert 로그에서 이상 패턴이 검출되지 않았습니다.',
            message='DB 엔진 로그 파일 점검 정상',
        )


CHECK_CLASS = Check
