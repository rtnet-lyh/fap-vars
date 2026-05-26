# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


DF_COMMAND = 'df -k $ORACLE_HOME'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'solaris'
    PARAMIKO_REUSE_SESSION = False

    def _parse_df(self, text):
        lines = [line.rstrip() for line in str(text or '').splitlines() if line.strip()]
        for index, line in enumerate(lines):
            lowered = [part.lower() for part in re.split(r'\s+', line.strip())]
            if 'filesystem' not in lowered or 'capacity' not in lowered or 'mounted' not in lowered:
                continue
            pending_filesystem = ''
            for row_line in lines[index + 1:]:
                parts = re.split(r'\s+', row_line.strip())
                if len(parts) == 1:
                    pending_filesystem = parts[0]
                    continue
                if pending_filesystem:
                    parts = [pending_filesystem] + parts
                    pending_filesystem = ''
                if len(parts) < 6 or not re.match(r'^\d+%$', parts[4]):
                    continue
                try:
                    return {
                        'filesystem': parts[0],
                        'total_kb': int(parts[1]),
                        'used_kb': int(parts[2]),
                        'available_kb': int(parts[3]),
                        'used_percent': int(parts[4].rstrip('%')),
                        'mounted_on': ' '.join(parts[5:]),
                    }
                except ValueError:
                    continue
            return None
        return None

    def run(self):
        oracle_account = self.get_threshold_var('oracle_account', default='oratips', value_type='str')
        max_used_percent = self.get_threshold_var('max_used_percent', default=80, value_type='int')
        try:
            result = self._run_solaris_account_commands(
                oracle_account,
                [{'command': DF_COMMAND, 'timeout': 10}],
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
            return self.fail('df 명령 실행 실패', message='아카이브 로그 파일시스템 사용률을 확인하지 못했습니다.', stdout=stdout, stderr=stderr)

        row = self._parse_df(stdout)
        if not row:
            return self.fail('df 출력 파싱 실패', message='df -k 출력에서 아카이브 로그 파일시스템 행을 해석하지 못했습니다.', stdout=stdout, stderr=stderr)

        metrics = {
            'oracle_account': oracle_account,
            'verified_oracle_account': switch.get('actual_user') or '',
        }
        metrics.update(row)
        thresholds = {'oracle_account': oracle_account, 'max_used_percent': max_used_percent}
        if row['used_percent'] > max_used_percent:
            return self.fail(
                '아카이브 로그 파일시스템 사용률 임계치 초과',
                metrics=metrics,
                thresholds=thresholds,
                reasons='파일시스템 사용률이 기준을 초과했습니다.',
                message='아카이브 로그 파일시스템 사용률 %s%%가 기준 %s%%를 초과했습니다.' % (row['used_percent'], max_used_percent),
            )
        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='파일시스템 사용률이 기준 이하입니다.',
            message='아카이브 로그 파일시스템 사용률 정상: %s%%, 기준 %s%%' % (row['used_percent'], max_used_percent),
        )


CHECK_CLASS = Check
