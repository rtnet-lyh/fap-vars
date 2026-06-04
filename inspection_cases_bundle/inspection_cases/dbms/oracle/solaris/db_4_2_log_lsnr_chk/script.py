# -*- coding: utf-8 -*-

import shlex
import re

from .common._base import BaseCheck


# LSNR_PATTERN = 'connection refused|timeout|TNS listener stopped|warning|slow|delay|TNS-12514|TNS-12541|TNS-12170'
LSNR_PATTERN = 'TNS-|ORA-|WARNING|FATAL|REFUSED|FAILED'
FIND_LISTENER_COMMAND = "find /TTIPS_GRID /TTIPS_HOME /oracle/app/oracle/diag/tnslsnr/citsdb1/listener/trace -type f -name 'listener.log' 2>/dev/null | xargs ls -t | head -1"

class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'solaris'
    PARAMIKO_REUSE_SESSION = False

    def run(self):
        oracle_account = self.get_threshold_var('oracle_account', default='oratips', value_type='str')

        # log 경로를 찾기위한 쿼리 실행
        try:
            result = self._run_solaris_account_commands(
                oracle_account,
                [{'command': FIND_LISTENER_COMMAND, 'timeout': 20}],
            )[0]
        except ValueError as exc:
            return self.fail('Oracle 계정 전환 설정 오류', message=str(exc))

        switch = getattr(self, '_solaris_last_account_switch_verification', {}) or {}
        if not switch.get('ok'):
            return self.fail('Oracle 계정 전환 실패', message=switch.get('message') or 'Oracle 계정 전환을 확인하지 못했습니다.', stdout=switch.get('stdout') or '', stderr=switch.get('stderr'))

        stdout = result.get('stdout', '').splitlines()[-1]
        match = re.search(r"(/[\w./-]+)", stdout)
        listener_log = match.group(1) if match else False
        if not listener_log:
            return self.fail('listener_log 검색 실패', message='listener_log 검색 실패')        
        
        # command = f'egrep -i "{LSNR_PATTERN}" {listener_log} | tail -200'
        command = f'tail -2000 {listener_log} | egrep -i "{LSNR_PATTERN}"'

        result = self._run_paramiko_commands(                
            [{'command': command, 'timeout': 20}],
            become=True
        )[0]
        
        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()        
        
        if result.get('rc') not in (0, 1):
            return self.fail('리스너 로그 grep 실행 실패', message='리스너 로그 파일 검색 명령을 실행하지 못했습니다.', stdout=stdout, stderr=stderr)

        lines = [line for line in stdout.splitlines() if line.strip()]
        metrics = {
            'oracle_account': oracle_account,
            'verified_oracle_account': switch.get('actual_user') or '',
            'matched_log_count': len(lines),
            'matched_logs': lines,
        }
        thresholds = {'oracle_account': oracle_account}
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