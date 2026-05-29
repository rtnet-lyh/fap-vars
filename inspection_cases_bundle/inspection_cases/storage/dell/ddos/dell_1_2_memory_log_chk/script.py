# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


COMMAND_ERROR_MARKERS = ('syntax error', 'unknown command', 'invalid command', 'command not found')
COMMAND = 'alerts show current'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'generic_network'
    PARAMIKO_REUSE_SESSION = True

    def _detect_cli_error(self, *texts):
        for text in texts:
            for line in str(text or '').splitlines():
                stripped = line.strip()
                lowered = stripped.lower()
                if stripped and any(marker in lowered for marker in COMMAND_ERROR_MARKERS):
                    return stripped
        return ''

    def _run_command(self):
        results = self._run_paramiko_commands([COMMAND], profile=self.PARAMIKO_PROFILE)
        if not results:
            return None, self.fail('점검 명령 실행 실패', message='Paramiko 명령 실행 결과가 비어 있습니다.')
        result = results[0]
        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()
        if result.get('rc') != 0:
            return None, self.fail('점검 명령 실행 실패', message=f'{COMMAND} 명령 실행에 실패했습니다.', stdout=stdout, stderr=stderr)
        error_text = self._detect_cli_error(stdout, stderr)
        if error_text:
            return None, self.fail('점검 명령 실행 실패', message=f'{COMMAND} 명령 출력에서 오류가 확인되었습니다: {error_text}', stdout=stdout, stderr=stderr)
        return stdout, None

    def _parse_alerts(self, text):
        active_match = re.search(r'There\s+(?:is|are)\s+(\d+)\s+active alert', text, re.IGNORECASE)
        active_alert_count = int(active_match.group(1)) if active_match else 0
        bad_severity_lines = [line.strip() for line in text.splitlines() if re.search(r'\b(ERROR|CRITICAL)\b', line, re.IGNORECASE)]
        return {'active_alert_count': active_alert_count, 'bad_severity_lines': bad_severity_lines}

    def run(self):
        stdout, error = self._run_command()
        if error:
            return error

        metrics = self._parse_alerts(stdout)
        if metrics['active_alert_count'] > 0 or metrics['bad_severity_lines']:
            return self.fail('Alert 상태 기준 미달', message='Active Alert 또는 ERROR/CRITICAL Severity가 확인되었습니다.', stdout=stdout, metrics=metrics, thresholds={})
        return self.ok(metrics=metrics, thresholds={}, reasons='Active Alert와 ERROR/CRITICAL Severity가 없습니다.', message='Alert 상태 점검 정상.')


CHECK_CLASS = Check
