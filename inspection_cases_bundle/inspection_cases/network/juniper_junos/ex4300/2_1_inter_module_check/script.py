# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


COMMAND_ERROR_MARKERS = ('syntax error', 'unknown command', 'invalid command', 'unknown keyword', 'missing argument')
COMMAND = 'show interfaces terse'


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

    def _parse_interface_states(self, text):
        rows = []
        for line in (text or '').splitlines():
            match = re.match(r'^(\S+)\s+(up|down)\s+(up|down)(?:\s|$)', line.strip(), re.IGNORECASE)
            if match:
                rows.append({'interface': match.group(1), 'admin': match.group(2).lower(), 'link': match.group(3).lower()})
        return rows

    def run(self):
        stdout, error = self._run_command(COMMAND)
        if error:
            return error

        interfaces = self._parse_interface_states(stdout)
        if not interfaces:
            return self.fail('인터페이스 상태 파싱 실패', message='show interfaces terse 출력에서 인터페이스 상태 행을 찾지 못했습니다.', stdout=stdout)
        bad_interfaces = [item for item in interfaces if item['admin'] == 'up' and item['link'] != 'up']
        metrics = {
            'interface_count': len(interfaces),
            'bad_interface_count': len(bad_interfaces),
            'bad_interfaces': bad_interfaces,
            'interfaces': interfaces,
        }
        if bad_interfaces:
            return self.fail('인터페이스 상태 기준 미달', message=f'admin up/link down 인터페이스가 {len(bad_interfaces)}개 있습니다.', stdout=stdout, metrics=metrics, thresholds={})
        return self.ok(metrics=metrics, thresholds={}, reasons='admin up 인터페이스의 link가 모두 up입니다.', message='인터페이스/모듈 상태 점검 정상.')


CHECK_CLASS = Check
