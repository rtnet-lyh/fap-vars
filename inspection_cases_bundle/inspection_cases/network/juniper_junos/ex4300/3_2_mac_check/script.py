# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


COMMAND_ERROR_MARKERS = ('syntax error', 'unknown command', 'invalid command', 'unknown keyword', 'missing argument')
COMMAND = 'show arp'
MAC_RE = re.compile(r'^[0-9a-f]{2}(?::[0-9a-f]{2}){5}$', re.IGNORECASE)
IP_RE = re.compile(r'^\d+(?:\.\d+){3}$')


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

    def _parse_arp_entries(self, text):
        entries = []
        for line in (text or '').splitlines():
            parts = line.split()
            if len(parts) >= 4 and MAC_RE.match(parts[0]) and IP_RE.match(parts[1]):
                entries.append({'mac_address': parts[0], 'ip_address': parts[1], 'name': parts[2], 'interface': parts[3]})
        return entries

    def run(self):
        stdout, error = self._run_command(COMMAND)
        if error:
            return error

        entries = self._parse_arp_entries(stdout)
        metrics = {'arp_entry_count': len(entries), 'arp_entries': entries}
        if not entries:
            return self.fail('MAC/ARP 파싱 실패', message='show arp 출력에서 MAC/IP/interface 행을 찾지 못했습니다.', stdout=stdout, metrics=metrics, thresholds={})
        return self.ok(metrics=metrics, thresholds={}, reasons='MAC/IP/interface 행이 1개 이상 정상 파싱되었습니다.', message=f'MAC/ARP 테이블 점검 정상: {len(entries)}개 항목.')


CHECK_CLASS = Check
