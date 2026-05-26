# -*- coding: utf-8 -*-

from .common._base import BaseCheck


PS_COMMAND = 'ps aux | grep ora_smon'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'solaris'
    PARAMIKO_REUSE_SESSION = False

    def _smon_lines(self, text):
        lines = []
        for line in str(text or '').splitlines():
            stripped = line.strip()
            if 'ora_smon' not in stripped or 'grep ora_smon' in stripped:
                continue
            lines.append(stripped)
        return lines

    def run(self):
        oracle_account = self.get_threshold_var('oracle_account', default='oratips', value_type='str')
        try:
            result = self._run_solaris_account_commands(
                oracle_account,
                [{'command': PS_COMMAND, 'timeout': 10}],
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
            return self.fail('ps 명령 실행 실패', message='Oracle smon 프로세스 상태를 확인하지 못했습니다.', stdout=stdout, stderr=stderr)

        lines = self._smon_lines(stdout)
        metrics = {
            'oracle_account': oracle_account,
            'verified_oracle_account': switch.get('actual_user') or '',
            'smon_process_count': len(lines),
            'smon_process_lines': lines,
        }
        thresholds = {'oracle_account': oracle_account}
        if not lines:
            return self.fail(
                'Oracle smon 프로세스 미확인',
                metrics=metrics,
                thresholds=thresholds,
                message='ps 출력에서 Oracle DBMS 메인 프로세스 ora_smon을 찾지 못했습니다.',
                stdout=stdout,
                stderr=stderr,
            )
        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='grep 프로세스를 제외한 ora_smon 프로세스가 확인되었습니다.',
            message='Oracle DBMS 메인 프로세스 기동 상태 정상: ora_smon %s건' % len(lines),
        )


CHECK_CLASS = Check
