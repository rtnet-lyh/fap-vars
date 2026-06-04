# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


COMMANDS = ['show mac', 'show arp']
MAC_RE = re.compile(r'^[0-9a-f]{2}(?::[0-9a-f]{2}){5}$', re.IGNORECASE)
IP_RE = re.compile(r'^\d+(?:\.\d+){3}$')


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'generic_network'
    PARAMIKO_REUSE_SESSION = True

    def _run_commands(self):
        results = self._run_paramiko_commands(COMMANDS, profile=self.PARAMIKO_PROFILE)
        if not results:
            return None, self.fail('점검 명령 실행 실패', message='Paramiko 명령 실행 결과가 비어 있습니다.')
        if len(results) < len(COMMANDS):
            return None, self.fail('점검 명령 실행 실패', message='일부 점검 명령 결과를 수신하지 못했습니다.')
        for result in results:
            stdout = (result.get('stdout') or '').strip()
            stderr = (result.get('stderr') or '').strip()
            if result.get('rc') != 0:
                return None, self.fail('점검 명령 실행 실패', message=f'{result.get("command")} 명령 실행에 실패했습니다.', stdout=stdout, stderr=stderr)
        return results, None

    def _split_list(self, value):
        return [item.strip().upper() for item in re.split(r'[,|\n]+', str(value or '')) if item.strip()]

    def _parse_mac_entries(self, text):
        entries = []
        current_port = ''
        current_vid = ''
        for line in (text or '').splitlines():
            parts = line.split()
            if not parts:
                continue
            if MAC_RE.match(parts[0]) and len(parts) >= 3:
                mac, status, entry_type = parts[0], parts[1], parts[2]
            elif len(parts) >= 5 and MAC_RE.match(parts[2]):
                current_port, current_vid = parts[0], parts[1]
                mac, status, entry_type = parts[2], parts[3], parts[4]
            else:
                continue
            entries.append({
                'port': current_port,
                'vid': current_vid,
                'mac_address': mac,
                'status': status.lower(),
                'type': entry_type.lower(),
            })
        return entries

    def _parse_arp_entries(self, text):
        entries = []
        for line in (text or '').splitlines():
            parts = line.split()
            if len(parts) < 4 or not IP_RE.match(parts[0]) or not MAC_RE.match(parts[1]):
                continue
            entries.append({
                'ip_address': parts[0],
                'mac_address': parts[1],
                'interface': parts[2],
                'state': parts[3].upper(),
            })
        return entries

    def run(self):
        expected_mac_status = str(self.get_threshold_var('expected_mac_status', default='forward', value_type='str')).strip().lower()
        valid_arp_state_raw = self.get_threshold_var('valid_arp_state', default='REACHABLE,STALE,DELAY', value_type='str')
        valid_arp_states = self._split_list(valid_arp_state_raw)
        thresholds = {'expected_mac_status': expected_mac_status, 'valid_arp_state': valid_arp_states}
        results, error = self._run_commands()
        if error:
            return error

        mac_stdout = (results[0].get('stdout') or '').strip()
        arp_stdout = (results[1].get('stdout') or '').strip()
        mac_entries = self._parse_mac_entries(mac_stdout)
        arp_entries = self._parse_arp_entries(arp_stdout)
        if not mac_entries or not arp_entries:
            return self.fail('MAC/ARP 파싱 실패', message='show mac 또는 show arp 출력에서 테이블 항목을 찾지 못했습니다.', stdout='\n\n'.join([mac_stdout, arp_stdout]), thresholds=thresholds, metrics={'mac_entry_count': len(mac_entries), 'arp_entry_count': len(arp_entries)})

        invalid_mac_entries = [
            item for item in mac_entries
            if not item['port'] or item['status'] != expected_mac_status
        ]
        invalid_arp_entries = [item for item in arp_entries if item['state'] not in valid_arp_states]
        metrics = {
            'mac_entry_count': len(mac_entries),
            'arp_entry_count': len(arp_entries),
            'invalid_mac_entries': invalid_mac_entries,
            'invalid_arp_entries': invalid_arp_entries,
            'mac_entries': mac_entries[:10],
            'arp_entries': arp_entries[:10],
        }
        if invalid_mac_entries or invalid_arp_entries:
            return self.warn(metrics=metrics, thresholds=thresholds, reasons='MAC status 또는 ARP state 기준을 만족하지 않는 항목이 있습니다.', message=f'MAC/ARP 상태 경고: MAC {len(invalid_mac_entries)}개, ARP {len(invalid_arp_entries)}개.')
        return self.ok(metrics=metrics, thresholds=thresholds, reasons='MAC status와 ARP state가 기준을 만족합니다.', message=f'MAC/ARP 테이블 점검 정상: MAC {len(mac_entries)}개, ARP {len(arp_entries)}개.')


CHECK_CLASS = Check
