# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


COMMAND_ERROR_MARKERS = ('syntax error', 'unknown command', 'invalid command', 'unknown keyword', 'missing argument')
COMMAND = 'show vlans'


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

    def _split_list(self, value):
        return [item.strip() for item in re.split(r'[,|\n]+', str(value or '')) if item.strip()]

    def _parse_vlan_names(self, text):
        names = []
        for line in (text or '').splitlines():
            parts = line.split()
            if len(parts) >= 3 and re.match(r'^\d+$', parts[2]):
                names.append(parts[1])
        return names

    def run(self):
        active_names = self._split_list(self.get_threshold_var('active_vlan_name', default='v808', value_type='str'))
        thresholds = {'active_vlan_name': active_names}
        if not active_names:
            return self.fail('임계치 미정의', message='active_vlan_name threshold 값이 필요합니다.', thresholds=thresholds)

        stdout, error = self._run_command(COMMAND)
        if error:
            return error

        vlan_names = self._parse_vlan_names(stdout)
        if not vlan_names:
            return self.fail('VLAN 파싱 실패', message='show vlans 출력에서 VLAN name을 찾지 못했습니다.', stdout=stdout, thresholds=thresholds)
        missing = [name for name in active_names if name not in vlan_names]
        metrics = {'vlan_names': vlan_names, 'missing_vlan_names': missing}
        if missing:
            return self.fail('VLAN 상태 기준 미달', message=f'운영대상 VLAN이 출력에 없습니다: {", ".join(missing)}', stdout=stdout, metrics=metrics, thresholds=thresholds)
        return self.ok(metrics=metrics, thresholds=thresholds, reasons='운영대상 VLAN name이 출력에 존재합니다.', message='VLAN 상태 점검 정상.')


CHECK_CLASS = Check
