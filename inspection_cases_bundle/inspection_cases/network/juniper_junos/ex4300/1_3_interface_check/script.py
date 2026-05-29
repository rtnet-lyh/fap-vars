# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


COMMAND_ERROR_MARKERS = ('syntax error', 'unknown command', 'invalid command', 'unknown keyword', 'missing argument')
COMMAND_TEMPLATE = 'show interfaces {interface_name} statistics'


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

    def _speed_to_bps(self, value, unit):
        number = float(value)
        normalized = str(unit or '').strip().lower()
        if normalized.startswith('g'):
            return number * 1000 * 1000 * 1000
        if normalized.startswith('m'):
            return number * 1000 * 1000
        if normalized.startswith('k'):
            return number * 1000
        return number

    def _parse_interface_usage(self, text, interface_name):
        speed_match = re.search(r'\bSpeed:\s*([0-9.]+)\s*([kmg]?bps)', text, re.IGNORECASE)
        input_match = re.search(r'Input rate\s*:\s*(\d+)\s+bps', text, re.IGNORECASE)
        output_match = re.search(r'Output rate\s*:\s*(\d+)\s+bps', text, re.IGNORECASE)
        if not speed_match or not input_match or not output_match:
            return None
        speed_bps = self._speed_to_bps(speed_match.group(1), speed_match.group(2))
        input_bps = int(input_match.group(1))
        output_bps = int(output_match.group(1))
        input_percent = round((input_bps / speed_bps) * 100, 4) if speed_bps else 0.0
        output_percent = round((output_bps / speed_bps) * 100, 4) if speed_bps else 0.0
        return {
            'interface_name': interface_name,
            'speed_bps': int(speed_bps),
            'input_rate_bps': input_bps,
            'output_rate_bps': output_bps,
            'input_usage_percent': input_percent,
            'output_usage_percent': output_percent,
            'max_usage_percent': max(input_percent, output_percent),
        }

    def run(self):
        interface_name = str(self.get_threshold_var('interface_name', default='', value_type='str')).strip()
        max_usage = self.get_threshold_var('max_interface_usage_percent', default=80.0, value_type='float')
        thresholds = {'interface_name': interface_name, 'max_interface_usage_percent': max_usage}
        if not interface_name:
            return self.fail('임계치 미정의', message='interface_name threshold 값이 필요합니다.', thresholds=thresholds)

        command = COMMAND_TEMPLATE.format(interface_name=interface_name)
        stdout, error = self._run_command(command)
        if error:
            return error

        metrics = self._parse_interface_usage(stdout, interface_name)
        if not metrics:
            return self.fail('인터페이스 사용률 파싱 실패', message='인터페이스 속도 또는 입출력 rate 값을 해석하지 못했습니다.', stdout=stdout, thresholds=thresholds)
        if metrics['max_usage_percent'] > max_usage:
            return self.fail('인터페이스 사용률 임계치 초과', message=f'인터페이스 사용률 최대값 {metrics["max_usage_percent"]}%가 기준 {max_usage}%를 초과했습니다.', stdout=stdout, metrics=metrics, thresholds=thresholds)
        return self.ok(metrics=metrics, thresholds=thresholds, reasons='인터페이스 입출력 사용률이 임계치 이하입니다.', message=f'인터페이스 사용률 점검 정상: 최대 {metrics["max_usage_percent"]}%.')


CHECK_CLASS = Check
