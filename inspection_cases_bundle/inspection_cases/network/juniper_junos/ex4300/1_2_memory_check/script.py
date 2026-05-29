# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


COMMAND_ERROR_MARKERS = ('syntax error', 'unknown command', 'invalid command', 'unknown keyword', 'missing argument')
COMMAND = 'show system memory'


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

    def _parse_memory_usage(self, text):
        total_match = re.search(r'Total memory:\s*(\d+)\s+Kbytes\s*\(\s*100%\)', text, re.IGNORECASE)
        free_match = re.search(r'Free memory:\s*(\d+)\s+Kbytes\s*\(\s*([0-9.]+)%\s*\)', text, re.IGNORECASE)
        if not total_match or not free_match:
            return None
        free_percent = float(free_match.group(2))
        return {
            'memory_total_kb': int(total_match.group(1)),
            'memory_free_kb': int(free_match.group(1)),
            'memory_free_percent': round(free_percent, 2),
            'memory_usage_percent': round(max(0.0, 100.0 - free_percent), 2),
        }

    def run(self):
        max_usage = self.get_threshold_var('max_mem_usage_percent', default=80.0, value_type='float')
        thresholds = {'max_mem_usage_percent': max_usage}
        stdout, error = self._run_command(COMMAND)
        if error:
            return error

        metrics = self._parse_memory_usage(stdout)
        if not metrics:
            return self.fail('메모리 사용률 파싱 실패', message='메모리 사용률 값을 해석하지 못했습니다.', stdout=stdout, thresholds=thresholds)
        if metrics['memory_usage_percent'] > max_usage:
            return self.fail('메모리 사용률 임계치 초과', message=f'메모리 사용률 {metrics["memory_usage_percent"]}%가 기준 {max_usage}%를 초과했습니다.', stdout=stdout, metrics=metrics, thresholds=thresholds)
        return self.ok(metrics=metrics, thresholds=thresholds, reasons='메모리 사용률이 임계치 이하입니다.', message=f'메모리 사용률 점검 정상: {metrics["memory_usage_percent"]}%.')


CHECK_CLASS = Check
