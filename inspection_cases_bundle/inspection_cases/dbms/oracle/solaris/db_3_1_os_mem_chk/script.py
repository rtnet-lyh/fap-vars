# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


MEMORY_COMMAND = 'ps -eo pid,comm,pmem,rss,vsz | grep ora_'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'solaris'
    PARAMIKO_REUSE_SESSION = False

    def _parse_rows(self, text):
        rows = []
        for line in str(text or '').splitlines():
            parts = re.split(r'\s+', line.strip())
            if len(parts) < 5 or not parts[1].startswith('ora_'):
                continue
            try:
                rows.append({
                    'pid': int(parts[0]),
                    'command': parts[1],
                    'memory_percent': float(parts[2]),
                    'rss_kb': int(parts[3]),
                    'vsz_kb': int(parts[4]),
                })
            except ValueError:
                continue
        return rows

    def run(self):
        oracle_account = self.get_threshold_var('oracle_account', default='oratips', value_type='str')
        max_memory_percent = self.get_threshold_var('max_memory_percent', default=80, value_type='float')
        try:
            result = self._run_solaris_account_commands(
                oracle_account,
                [{'command': MEMORY_COMMAND, 'timeout': 10}],
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
            return self.fail('ps 명령 실행 실패', message='Oracle 프로세스 메모리 정보를 확인하지 못했습니다.', stdout=stdout, stderr=stderr)

        rows = self._parse_rows(stdout)
        if not rows:
            return self.fail('메모리 출력 파싱 실패', message='ps 출력에서 Oracle 메모리 사용 행을 해석하지 못했습니다.', stdout=stdout, stderr=stderr)

        max_row = max(rows, key=lambda row: row['memory_percent'])        
        is_pass = True if max_row['memory_percent'] <= max_memory_percent else False

        if is_pass:
             return self.ok(                
                metrics={
                    'applicable': False,
                    'oracle_account': oracle_account,
                    'verified_oracle_account': switch.get('actual_user') or '',
                    'process_count': len(rows),
                    'max_memory_percent': max_row['memory_percent'],
                    'max_memory_process': max_row['command'],
                    'top_10_processes': rows[0:10],
                },
                thresholds={'oracle_account': oracle_account},
                reasons=f"메모리 사용률({max_row['memory_percent']}%) 정상. 임계치: {max_memory_percent}%",
                message=f"메모리 사용률({max_row['memory_percent']}%) 정상. 임계치: {max_memory_percent}%",
            )
        else:
            return self.fail(
                error=f"메모리 사용률({max_row['memory_percent']}%) 임계치({max_memory_percent}%) 초과",
                metrics={
                    'applicable': False,
                    'oracle_account': oracle_account,
                    'verified_oracle_account': switch.get('actual_user') or '',
                    'process_count': len(rows),
                    'max_memory_percent': max_row['memory_percent'],
                    'max_memory_process': max_row['command'],
                    'top_10_processes': rows[0:10],
                },
                thresholds={'oracle_account': oracle_account},
                reasons=f"메모리 사용률({max_row['memory_percent']}%) 점검필요. 임계치: {max_memory_percent}%",
                message=f"메모리 사용률({max_row['memory_percent']}%) 점검필요. 임계치: {max_memory_percent}%",
            )


CHECK_CLASS = Check
