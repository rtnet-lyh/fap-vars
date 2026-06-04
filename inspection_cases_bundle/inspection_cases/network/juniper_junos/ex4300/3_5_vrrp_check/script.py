# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck

COMMAND_ERROR_MARKERS = ('syntax error', 'unknown command', 'invalid command', 'unknown keyword', 'missing argument')
COMMAND = 'show vrrp summary'

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

    def run(self):
        stdout, error = self._run_command(COMMAND)
        if error:
            return error

        output_lines = [line.strip() for line in stdout.splitlines() if line.strip()]
        metrics = {'output_line_count': len(output_lines), 'output_lines': output_lines}
        if not output_lines:
            return self.fail('VRRP 상태 기준 미달', message='show vrrp summary 출력이 비어 있습니다.', stdout=stdout, metrics=metrics, thresholds={})
        
        message = 'VRRP 미설정 장비 입니다.' if re.search(r'vrrp subsystem not running', stdout) else '이중화 구성 상태 점검 정상.' # to do 
        return self.ok(metrics=metrics, thresholds={}, reasons=message, message=message)


CHECK_CLASS = Check
