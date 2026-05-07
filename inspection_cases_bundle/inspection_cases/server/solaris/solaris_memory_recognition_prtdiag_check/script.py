# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


MEMORY_COMMAND = 'prtdiag; prtconf -v | grep -i memory'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_AUTH_TIMEOUT_SEC = 30

    def _is_become_enabled(self):
        value = self.get_connection_value('become', default=False)
        return str(value).strip().lower() in ('1', 'true', 'y', 'yes', 'on')

    def _build_become_command(self):
        method = str(self.get_connection_value('become_method', default='su -') or 'su -')
        method = ' '.join(method.strip().lower().split())
        user = str(self.get_connection_value('become_user', default='root') or 'root').strip() or 'root'

        if method == 'su':
            return 'su ' + user
        if method == 'su -':
            return 'su - ' + user
        if method == 'sudo':
            return 'sudo -u ' + user + ' -i'
        raise ValueError(f'unsupported become_method: {method}')

    def _build_paramiko_commands(self, command):
        if not self._is_become_enabled():
            return [command]

        return [
            {
                'command': self._build_become_command(),
                'timeout': 1,
                'ignore_prompt': True,
            },
            {
                'command': str(self.get_connection_value('become_password', default='') or ''),
                'hide_command': True,
            },
            command,
        ]

    def _run_check_command(self, command):
        try:
            results = self._run_paramiko_commands(self._build_paramiko_commands(command))
        except ValueError as exc:
            return 1, '', str(exc)

        for item in reversed(results):
            if item.get('command') == command:
                return item.get('rc'), item.get('stdout', ''), item.get('stderr', '')

        failed_result = next((item for item in results if item.get('rc') != 0), None)
        if failed_result:
            return failed_result.get('rc'), failed_result.get('stdout', ''), failed_result.get('stderr', '')
        return 1, '', 'paramiko command result not found'


    def _to_memory_mb(self, value, unit):
        try:
            number = float(str(value).strip())
        except (TypeError, ValueError):
            return None

        lowered_unit = str(unit or '').strip().lower()
        if lowered_unit.startswith('giga'):
            return round(number * 1024.0, 2)
        if lowered_unit.startswith('mega'):
            return round(number, 2)
        if lowered_unit.startswith('kilo'):
            return round(number / 1024.0, 2)
        return None

    def _parse_memory_size(self, text):
        match = re.search(r'Memory size:\s*([0-9]+(?:\.[0-9]+)?)\s*(Kilobytes|Megabytes|Gigabytes)', text or '', re.IGNORECASE)
        if not match:
            return None

        recognized_memory_mb = self._to_memory_mb(match.group(1), match.group(2))
        if recognized_memory_mb is None:
            return None

        return {
            'recognized_memory_mb': recognized_memory_mb,
            'recognized_memory_gib': round(recognized_memory_mb / 1024.0, 2),
            'memory_unit': match.group(2),
            'memory_value': match.group(1),
        }

    def _parse_dimm_entries(self, text):
        dimm_entries = []

        for line in (text or '').splitlines():
            stripped = line.strip()
            if not stripped or not re.match(r'^(DIMM|Memory Module)', stripped, re.IGNORECASE):
                continue

            if re.match(r'^DIMM\s+\d+:', stripped, re.IGNORECASE):
                slot_match = re.match(r'^(DIMM\s+\d+):\s*(.*)$', stripped, re.IGNORECASE)
                if not slot_match:
                    continue

                slot_name = slot_match.group(1)
                details = slot_match.group(2)
                size_match = re.search(r'([0-9]+(?:\.[0-9]+)?)\s*(KB|MB|GB)', details, re.IGNORECASE)
                size_mb = None
                if size_match:
                    size_value = size_match.group(1)
                    size_unit = size_match.group(2)
                    normalized_unit = {
                        'KB': 'Kilobytes',
                        'MB': 'Megabytes',
                        'GB': 'Gigabytes',
                    }.get(size_unit.upper(), size_unit)
                    size_mb = self._to_memory_mb(size_value, normalized_unit)

                dimm_entries.append({
                    'slot_name': slot_name,
                    'details': details,
                    'size_mb': size_mb,
                    'has_ecc': 'error correcting code' in details.lower() or 'ecc' in details.lower(),
                })

        return dimm_entries

    def run(self):
        expected_memory_mb = self.get_threshold_var('expected_memory_mb', default=0, value_type='int')
        min_dimm_count = self.get_threshold_var('min_dimm_count', default=1, value_type='int')
        failure_keywords_raw = self.get_threshold_var('failure_keywords', default='', value_type='str')

        rc, out, err = self._run_check_command(MEMORY_COMMAND)

        if self._is_connection_error(rc, err):
            return self.fail('호스트 연결 실패', message=(err or 'SSH 연결 확인에 실패했습니다.').strip(), stderr=(err or '').strip())

        if rc != 0:
            return self.fail('점검 명령 실행 실패', message='Solaris 메모리 상태 점검에 실패했습니다. 현재 상태: prtdiag/prtconf 명령을 정상적으로 실행하지 못했습니다.', stdout=(out or '').strip(), stderr=(err or '').strip())

        command_error = self._detect_command_error(out, err, extra_patterns=['permission denied', 'not supported', 'unknown userland error'])
        if command_error:
            return self.fail('점검 명령 실행 실패', message=f'Solaris 메모리 상태 점검에 실패했습니다. 현재 상태: prtdiag/prtconf 출력에서 실행 오류가 확인되었습니다: {command_error}', stdout=(out or '').strip(), stderr=(err or '').strip())

        text = (out or '').strip()
        failure_keywords = [keyword.strip() for keyword in failure_keywords_raw.split(',') if keyword.strip()]
        combined_text = '\n'.join(part for part in (text, (err or '').strip()) if part)
        matched_failure_keywords = [keyword for keyword in failure_keywords if keyword.lower() in combined_text.lower()]
        if matched_failure_keywords:
            return self.fail('메모리 인식 실패 키워드 감지', message=f'Solaris 메모리 상태 점검에 실패했습니다. 현재 상태: 출력에서 실패 키워드 {matched_failure_keywords}가 확인되었습니다.', stdout=text, stderr=(err or '').strip())

        parsed_memory = self._parse_memory_size(text)
        if not parsed_memory:
            return self.fail('메모리 인식 정보 없음', message='Solaris 메모리 상태 점검에 실패했습니다. 현재 상태: prtdiag/prtconf 출력에서 Memory size 값을 찾지 못했습니다.', stdout=text, stderr=(err or '').strip())

        recognized_memory_mb = parsed_memory['recognized_memory_mb']
        recognized_memory_gib = parsed_memory['recognized_memory_gib']

        dimm_entries = self._parse_dimm_entries(text)
        dimm_count = len(dimm_entries)
        dimm_sized_entries = [entry for entry in dimm_entries if entry.get('size_mb') is not None]
        dimm_total_mb = round(sum(entry['size_mb'] for entry in dimm_sized_entries), 2) if dimm_sized_entries else 0.0
        ecc_dimm_count = len([entry for entry in dimm_entries if entry.get('has_ecc')])

        metrics = {
            'recognized_memory_mb': recognized_memory_mb,
            'recognized_memory_gib': recognized_memory_gib,
            'memory_value': parsed_memory['memory_value'],
            'memory_unit': parsed_memory['memory_unit'],
            'dimm_count': dimm_count,
            'dimm_total_mb': dimm_total_mb,
            'ecc_dimm_count': ecc_dimm_count,
            'dimm_entries': dimm_entries,
            'matched_failure_keywords': matched_failure_keywords,
        }
        thresholds = {
            'expected_memory_mb': expected_memory_mb,
            'min_dimm_count': min_dimm_count,
            'failure_keywords': failure_keywords,
        }

        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons=f'Memory size 값 {recognized_memory_mb:.2f}MB ({recognized_memory_gib:.2f}GiB)을 정상 수집했습니다.',
            message=f'Solaris 메모리 상태가 정상입니다. 현재 상태: Memory size {recognized_memory_mb:.2f}MB ({recognized_memory_gib:.2f}GiB)를 수집했습니다.',
        )


CHECK_CLASS = Check
