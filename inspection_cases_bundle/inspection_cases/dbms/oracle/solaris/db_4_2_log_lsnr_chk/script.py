# -*- coding: utf-8 -*-

import shlex

from .common._base import BaseCheck


LSNR_PATTERN = 'connection refused|timeout|TNS listener stopped|warning|slow|delay|TNS-12514|TNS-12541|TNS-12170'
DEFAULT_LSNR_LOG_DIR = '/TTIPS_GRID/oracle/grid/gridbase/diag/tnslsnr/exTMStotalDB1/listener/trace'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'solaris'
    PARAMIKO_REUSE_SESSION = False

    def run(self):
        oracle_account = self.get_threshold_var('oracle_account', default='oratips', value_type='str')
        lsnr_log_dir = self.get_threshold_var('lsnr_log_dir', default=DEFAULT_LSNR_LOG_DIR, value_type='str')
        listener_log = shlex.quote(lsnr_log_dir) + '/listener.log'
        command = 'tail -200 %s | egrep -i "%s" %s' % (listener_log, LSNR_PATTERN, listener_log)
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
            return self.fail('리스너 로그 grep 실행 실패', message='리스너 로그 파일 검색 명령을 실행하지 못했습니다.', stdout=stdout, stderr=stderr)

        lines = [line for line in stdout.splitlines() if line.strip()]
        metrics = {
            'oracle_account': oracle_account,
            'verified_oracle_account': switch.get('actual_user') or '',
            'matched_log_count': len(lines),
            'matched_logs': lines,
        }
        thresholds = {'oracle_account': oracle_account, 'lsnr_log_dir': lsnr_log_dir}
        if lines:
            return self.fail(
                '리스너 로그 이상 감지',
                metrics=metrics,
                thresholds=thresholds,
                message='리스너 로그에서 접속 이상 패턴 %s건이 확인되었습니다.' % len(lines),
                stdout=stdout,
                stderr=stderr,
            )
        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='리스너 로그에서 접속 이상 패턴이 검출되지 않았습니다.',
            message='리스너 로그 파일 점검 정상',
        )


CHECK_CLASS = Check
