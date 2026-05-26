# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


CONTROLFILE_COMMAND = """sqlplus -S /nolog <<EOF
CONNECT / AS SYSDBA
set linesize 200
col name format a40
SELECT * FROM V\$controlfile;
EXIT;
EOF"""


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'solaris'
    PARAMIKO_REUSE_SESSION = False

    def _mount(self, path):
        parts = str(path or '').split('/')
        return '/' + parts[1] if len(parts) > 1 and parts[1] else '/'

    def _parse_paths(self, text):
        return re.findall(r'(?m)(/\S+\.ctl)\b', str(text or ''))

    def run(self):
        oracle_account = self.get_threshold_var('oracle_account', default='oratips', value_type='str')
        try:
            result = self._run_solaris_account_commands(
                oracle_account,
                [{'command': CONTROLFILE_COMMAND, 'timeout': 30}],
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
            return self.fail('controlfile SQL 실행 실패', message='controlfile 이중화 SQL을 실행하지 못했습니다.', stdout=stdout, stderr=stderr)

        paths = self._parse_paths(stdout)
        if not paths:
            return self.fail('controlfile 출력 파싱 실패', message='SQLPlus 출력에서 control file 경로를 찾지 못했습니다.', stdout=stdout, stderr=stderr)
        mounts = sorted(set(self._mount(path) for path in paths))
        has_invalid_status = bool(re.search(r'(?m)^\s*INVALID\s+/\S+\.ctl\b', stdout))
        metrics = {
            'oracle_account': oracle_account,
            'verified_oracle_account': switch.get('actual_user') or '',
            'control_file_count': len(paths),
            'control_file_paths': paths,
            'mount_points': mounts,
            'invalid_status_found': has_invalid_status,
        }
        thresholds = {'oracle_account': oracle_account}
        if has_invalid_status or len(paths) < 2 or len(mounts) < 2:
            return self.fail(
                'controlfile 이중화 기준 미달',
                metrics=metrics,
                thresholds=thresholds,
                message='control file이 2개 이상의 서로 다른 마운트 포인트에 분산되지 않았거나 INVALID 상태입니다.',
            )
        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='control file 경로가 2개 이상의 서로 다른 마운트 포인트에 있습니다.',
            message='controlfile 이중화 점검 정상',
        )


CHECK_CLASS = Check
