# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


COMMAND_ERROR_MARKERS = ('syntax error', 'unknown command', 'invalid command', 'command not found')
COMMANDS = ['system show hardware', 'alerts show current']
HBA_DEVICE_KEY = 'hba_device_keywords'
HBA_STATUS_KEY = 'hba_status_keywords'
DEFAULT_HBA_DEVICE_KEYWORDS = ['fibrechannel', 'fc', 'hba', 'scsi target']
DEFAULT_HBA_STATUS_KEYWORDS = ['offline', 'loop', 'link down']


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

    def _run_commands(self):
        commands = COMMANDS
        results = self._run_paramiko_commands(commands, profile=self.PARAMIKO_PROFILE)
        if not results:
            return None, self.fail('점검 명령 실행 실패', message='Paramiko 명령 실행 결과가 비어 있습니다.')
        if len(results) < len(commands):
            return None, self.fail('점검 명령 실행 실패', message='일부 점검 명령 결과를 수신하지 못했습니다.')
        for result in results:
            stdout = (result.get('stdout') or '').strip()
            stderr = (result.get('stderr') or '').strip()
            command = result.get('display_command') or result.get('command')
            if result.get('rc') != 0:
                return None, self.fail('점검 명령 실행 실패', message=f'{command} 명령 실행에 실패했습니다.', stdout=stdout, stderr=stderr)
            error_text = self._detect_cli_error(stdout, stderr)
            if error_text:
                return None, self.fail('점검 명령 실행 실패', message=f'{command} 명령 출력에서 오류가 확인되었습니다: {error_text}', stdout=stdout, stderr=stderr)
        stdout = '\n\n'.join((item.get('stdout') or '').strip() for item in results if (item.get('stdout') or '').strip()).strip()
        return stdout, None

    def _split_list(self, value):
        return [item.strip() for item in re.split(r'[,|\n]+', str(value or '')) if item.strip()]

    def _threshold_list(self, key, default_values):
        return self._split_list(self.get_threshold_var(key, default=','.join(default_values), value_type='str'))

    def _normalize(self, value):
        return re.sub(r'[^a-z0-9]+', '', str(value or '').lower())

    def _contains_keyword(self, text, keyword):
        normalized_keyword = self._normalize(keyword)
        if not normalized_keyword:
            return False
        if normalized_keyword == 'fc':
            lowered = str(text or '').lower()
            return 'fibrechannel' in self._normalize(text) or 'gbfc' in self._normalize(text) or re.search(r'\bfc\b', lowered) is not None
        return normalized_keyword in self._normalize(text)

    def _parse_hardware_rows(self, text):
        rows = []
        for line in text.splitlines():
            stripped = line.rstrip()
            if not stripped or stripped.startswith('Slot') or set(stripped.strip()) <= {'-'}:
                continue
            parts = re.split(r'\s{2,}', stripped.strip())
            if len(parts) < 3:
                continue
            slot, vendor, device = parts[:3]
            if slot.lower() in ('slot', '----') or vendor.lower() == 'vendor':
                continue
            rows.append({'slot': slot, 'vendor': vendor, 'device': device, 'ports': parts[3] if len(parts) >= 4 else ''})
        return rows

    def _valid_ports(self, value):
        text = str(value or '').strip()
        return bool(text and text.lower() != '(empty)')

    def _parse_alerts(self, text, device_keywords, status_keywords):
        active_match = re.search(r'There\s+(?:is|are)\s+(\d+)\s+active alert', text, re.IGNORECASE)
        active_alert_count = int(active_match.group(1)) if active_match else 0        
        keyword_lines = []
        for line in text.splitlines():
            if any(self._contains_keyword(line, keyword) for keyword in device_keywords) and any(self._contains_keyword(line, keyword) for keyword in status_keywords):
                keyword_lines.append(line.strip())
        return {
            'active_alert_count': active_alert_count,            
            'keyword_matched_alert_lines': keyword_lines,
        }

    def run(self):
        device_keywords = self._threshold_list(HBA_DEVICE_KEY, DEFAULT_HBA_DEVICE_KEYWORDS)
        status_keywords = self._threshold_list(HBA_STATUS_KEY, DEFAULT_HBA_STATUS_KEYWORDS)
        thresholds = {HBA_DEVICE_KEY: device_keywords, HBA_STATUS_KEY: status_keywords}
        stdout, error = self._run_commands()
        if error:
            return error

        rows = self._parse_hardware_rows(stdout)
        matching = [row for row in rows if any(self._contains_keyword(row['device'], keyword) for keyword in device_keywords)]
        rows_with_ports = [row for row in matching if self._valid_ports(row.get('ports'))]
        alert_metrics = self._parse_alerts(stdout, device_keywords, status_keywords)
        metrics = {
            'hardware_row_count': len(rows),
            'matching_device_count': len(matching),
            'matching_devices_with_ports_count': len(rows_with_ports),
            'matching_devices': matching,
        }
        metrics.update(alert_metrics)
        if not matching or not rows_with_ports or alert_metrics['keyword_matched_alert_lines']: # alert_metrics['active_alert_count'] > 0 or 
            return self.fail('하드웨어 상태 기준 미달', message='필수 장치/포트 정보가 없거나 관련 Alert 장애 조건이 확인되었습니다.', stdout=stdout, metrics=metrics, thresholds=thresholds)
        return self.ok(metrics=metrics, thresholds=thresholds, reasons='필수 장치와 포트 정보가 확인되고 관련 장애 조건이 없습니다.', message='HBA 로그 상태 점검 정상.')


CHECK_CLASS = Check
