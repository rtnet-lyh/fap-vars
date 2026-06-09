# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


COMMAND = 'show interfaces'
INTERFACE_RE = re.compile(
    r'^(?P<name>\S+) is (?P<status>administratively down|up|down), '
    r'line protocol is (?P<protocol>up|down)',
    re.IGNORECASE,
)
LOAD_RE = re.compile(r'txload\s+(\d+)/255,\s+rxload\s+(\d+)/255', re.IGNORECASE)
INPUT_ERROR_RE = re.compile(r'(\d+)\s+input errors,\s+(\d+)\s+CRC', re.IGNORECASE)
OUTPUT_ERROR_RE = re.compile(r'(\d+)\s+output errors', re.IGNORECASE)


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'cisco_ios'
    PARAMIKO_REUSE_SESSION = True

    def _set_enable_password(self):
        data = self.get_connection_credential_data()
        for key in ('en_password', 'become_password'):
            value = self.get_connection_value(key, None)
            if value not in (None, ''):
                if isinstance(data, dict) and not data.get('en_password'):
                    data['en_password'] = str(value)
                return True
            value = self.get_application_credential_value(key, None)
            if value not in (None, ''):
                if isinstance(data, dict) and not data.get('en_password'):
                    data['en_password'] = str(value)
                return True
        return False

    def _run_command(self):
        commands = [
            {'command': 'terminal length 0'},
            {'command': COMMAND},
        ]
        results = self._run_paramiko_commands(commands, enable_mode=self._set_enable_password())
        failed = [item for item in results if item.get('rc') != 0]
        if failed:
            first = failed[0]
            command = first.get('display_command') or first.get('command')
            return None, self.fail(
                '점검 명령 실행 실패',
                message=f'{command} 명령 실행에 실패했습니다.',
                stdout=(first.get('stdout') or '').strip(),
                stderr=(first.get('stderr') or '').strip(),
            )
        return (results[-1].get('stdout') or '').strip(), None

    def _parse_interfaces(self, text):
        rows = []
        current = None
        for line in (text or '').splitlines():
            iface = INTERFACE_RE.match(line.strip())
            if iface:
                if current:
                    rows.append(current)
                current = {
                    'interface': iface.group('name'),
                    'status': iface.group('status').lower(),
                    'protocol': iface.group('protocol').lower(),
                    'input_errors': 0,
                    'crc_errors': 0,
                    'output_errors': 0,
                }
                continue
            if not current:
                continue
            load = LOAD_RE.search(line)
            if load:
                txload = int(load.group(1))
                rxload = int(load.group(2))
                current['txload'] = txload
                current['rxload'] = rxload
                current['usage_percent'] = round(max(txload, rxload) / 255 * 100, 2)
            input_error = INPUT_ERROR_RE.search(line)
            if input_error:
                current['input_errors'] = int(input_error.group(1))
                current['crc_errors'] = int(input_error.group(2))
            output_error = OUTPUT_ERROR_RE.search(line)
            if output_error:
                current['output_errors'] = int(output_error.group(1))
        if current:
            rows.append(current)
        return [row for row in rows if 'usage_percent' in row]

    def run(self):
        max_usage = self.get_threshold_var('max_interface_usage_percent', default=80.0, value_type='float')
        max_errors = self.get_threshold_var('max_interface_error_count', default=0, value_type='int')
        thresholds = {
            'max_interface_usage_percent': max_usage,
            'max_interface_error_count': max_errors,
        }
        stdout, error = self._run_command()
        if error:
            return error

        interfaces = self._parse_interfaces(stdout)
        if not interfaces:
            return self.fail(
                '인터페이스 사용률 파싱 실패',
                message='show interfaces 출력에서 txload/rxload 값을 찾지 못했습니다.',
                stdout=stdout,
                thresholds=thresholds,
            )

        checked = [item for item in interfaces if item['status'] == 'up' and item['protocol'] == 'up']
        bad = []
        for item in checked:
            error_count = item['input_errors'] + item['crc_errors'] + item['output_errors']
            if item['usage_percent'] > max_usage or error_count > max_errors:
                bad.append(item)
        max_item = max(checked or interfaces, key=lambda item: item['usage_percent'])
        metrics = {
            'checked_interface_count': len(checked),
            'max_interface_usage_percent': max_item['usage_percent'],
            'max_interface': max_item['interface'],
            'bad_interfaces': bad,
            'interfaces': checked,
        }
        if bad:
            return self.warn(
                metrics=metrics,
                thresholds=thresholds,
                reasons='인터페이스 사용률 또는 에러 카운터가 기준을 초과했습니다.',
                message=f'인터페이스 트래픽 경고: 비정상 인터페이스 {len(bad)}개.',
            )
        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='인터페이스 사용률과 에러 카운터가 기준 이하입니다.',
            message=f'인터페이스 트래픽 점검 정상: 최대 사용률 {max_item["usage_percent"]}%.',
        )


CHECK_CLASS = Check
