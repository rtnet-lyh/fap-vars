# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck

COMMAND_ERROR_MARKERS = ('syntax error', 'unknown command', 'invalid command', 'unknown keyword', 'missing argument')
COMMAND = 'show interfaces statistics'

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

    def _run_command(self, command):
        results = self._run_paramiko_commands([{"command": command, "timeout": 10}], profile=self.PARAMIKO_PROFILE)
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

    def _parse_interface_usage(self, text):
        blocks = re.split(r'(?=Physical interface:)', text)
        blocks = [b.strip() for b in blocks if b.strip().startswith("Physical interface:")]
        force_1g_output = "Speed: 1000mbps"
        result = {}
        for block in blocks:
            is_forced = False
            match_interface = re.search(r'Physical interface:\s+(?P<interface>\S+),\s+.*Enabled.*Up', block)
            match_speed = re.search(r'Speed:\s+(?P<speed>\d+)(?P<unit>\w+)', block)
            if not match_speed:            
                match_speed = re.search(r'Speed:\s+(?P<speed>\d+)(?P<unit>\w+)', force_1g_output)
                is_forced = True
            match_input_bps = re.search(r'Input rate\s+:\s+(?P<input_bps>\d+)\s+bps', block)
            match_output_bps = re.search(r'Output rate\s+:\s+(?P<output_bps>\d+)\s+bps', block)
            if match_interface and match_speed and match_input_bps and match_output_bps:
                interface = match_interface.group("interface")
                speed = match_speed.group("speed")
                unit = match_speed.group("unit")
                input_bps = int(match_input_bps.group("input_bps"))
                output_bps = int(match_output_bps.group("output_bps"))
                speed_bps = self._speed_to_bps(speed, unit)
                result[interface] = {
                    "speed": speed + unit,                                                    
                    "input_bps": input_bps,
                    "input_percent": round((input_bps / speed_bps) * 100, 4) if speed_bps else 0.0,
                    "output_bps": output_bps,
                    "output_percent": round((output_bps / speed_bps) * 100, 4) if speed_bps else 0.0,
                    "is_forced": "대역폭 확인불가 - 1G로 간주" if is_forced else "대역폭 확인 성공",
                }

        return result

    def run(self):
        max_usage = self.get_threshold_var('max_interface_usage_percent', default=80.0, value_type='float')
        thresholds = {'max_interface_usage_percent': max_usage}
        
        stdout, error = self._run_command(COMMAND)
        if error:
            return error

        metrics = self._parse_interface_usage(stdout)
        if not metrics:
            return self.fail('인터페이스 사용률 파싱 실패', message='인터페이스 속도 또는 입출력 rate 값을 해석하지 못했습니다.', stdout=stdout, thresholds=thresholds)

        max_interface, max_data = max(
            metrics.items(),
            key=lambda item: max(
                item[1]["input_percent"],
                item[1]["output_percent"],
            )
        )

        real_max_usage = max(
            max_data["input_percent"],
            max_data["output_percent"],
        )

        if real_max_usage > max_usage:
            return self.fail('인터페이스 사용률 임계치 초과', message=f'인터페이스({max_interface}) 사용률 최대값 {real_max_usage}%가 기준 {max_usage}%를 초과했습니다.', stdout=stdout, metrics=metrics, thresholds=thresholds)
        return self.ok(metrics=metrics, thresholds=thresholds, reasons='인터페이스 입출력 사용률이 임계치 이하입니다.', message=f'인터페이스 사용률 점검 정상: 최대 {real_max_usage}%.')


CHECK_CLASS = Check
