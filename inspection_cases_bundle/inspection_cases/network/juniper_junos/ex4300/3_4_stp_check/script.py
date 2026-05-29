# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


COMMAND_ERROR_MARKERS = ('syntax error', 'unknown command', 'invalid command', 'unknown keyword', 'missing argument')
COMMAND = 'show spanning-tree interface'
VALID_STP_COMBINATIONS = {('FWD', 'DESG'), ('FWD', 'ROOT'), ('BLK', 'ALT'), ('DSC', 'ALT')}


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'generic_network'
    PARAMIKO_REUSE_SESSION = True

    def _run_command(self, command):
        results = self._run_paramiko_commands([command], profile=self.PARAMIKO_PROFILE)
        if not results:
            return None, self.fail('점검 명령 실행 실패', message='Paramiko 명령 실행 결과가 비어 있습니다.')
        result = results[0]
        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()
        if result.get('rc') != 0:
            return None, self.fail('점검 명령 실행 실패', message=f'{command} 명령 실행에 실패했습니다.', stdout=stdout, stderr=stderr)
        error_text = self._detect_cli_error(stdout, stderr)
        if error_text:
            return None, self.fail('점검 명령 실행 실패', message=f'{command} 명령 출력에서 오류가 확인되었습니다: {error_text}', stdout=stdout, stderr=stderr)
        return stdout, None

    def _detect_cli_error(self, *texts):
        for text in texts:
            for line in str(text or '').splitlines():
                stripped = line.strip()
                lowered = stripped.lower()
                if stripped and any(marker in lowered for marker in COMMAND_ERROR_MARKERS):
                    return stripped
        return ''

    def _parse_stp_rows(self, text):
        rows = []
        for line in (text or '').splitlines():
            parts = line.split()
            if len(parts) >= 7 and re.match(r'^[a-z]+-\d+/\d+/\d+$', parts[0], re.IGNORECASE):
                rows.append({'interface': parts[0], 'state': parts[-2].upper(), 'role': parts[-1].upper()})
        return rows

    def run(self):
        stdout, error = self._run_command(COMMAND)
        if error:
            return error

        rows = self._parse_stp_rows(stdout)
        if not rows:
            return self.fail('STP 파싱 실패', message='show spanning-tree interface 출력에서 STP 행을 찾지 못했습니다.', stdout=stdout, thresholds={})
        invalid = [row for row in rows if (row['state'], row['role']) not in VALID_STP_COMBINATIONS]
        metrics = {'stp_interface_count': len(rows), 'invalid_stp_interfaces': invalid, 'stp_interfaces': rows}
        if invalid:
            return self.fail('STP 상태 기준 미달', message=f'정상 State/Role 조합이 아닌 인터페이스가 {len(invalid)}개 있습니다.', stdout=stdout, metrics=metrics, thresholds={})
        return self.ok(metrics=metrics, thresholds={}, reasons='모든 STP State/Role 조합이 정상 범위입니다.', message='STP 상태 점검 정상.')


CHECK_CLASS = Check
