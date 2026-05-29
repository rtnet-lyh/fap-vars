# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


COMMAND_ERROR_MARKERS = ('syntax error', 'unknown command', 'invalid command', 'command not found')
COMMAND = 'ifgroup show config all'
DEFAULT_MIN_INTERFACE_COUNT = 1
DEFAULT_BAD_STATUS_KEYWORDS = ['disabled', 'down', 'offline', 'fail', 'error']


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

    def _run_command(self):
        results = self._run_paramiko_commands([COMMAND], profile=self.PARAMIKO_PROFILE)
        if not results:
            return None, self.fail('점검 명령 실행 실패', message='Paramiko 명령 실행 결과가 비어 있습니다.')
        result = results[0]
        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()
        if result.get('rc') != 0:
            return None, self.fail('점검 명령 실행 실패', message=f'{COMMAND} 명령 실행에 실패했습니다.', stdout=stdout, stderr=stderr)
        error_text = self._detect_cli_error(stdout, stderr)
        if error_text:
            return None, self.fail('점검 명령 실행 실패', message=f'{COMMAND} 명령 출력에서 오류가 확인되었습니다: {error_text}', stdout=stdout, stderr=stderr)
        return stdout, None

    def _split_list(self, value):
        return [item.strip() for item in re.split(r'[,|\n]+', str(value or '')) if item.strip()]

    def _parse_ifgroup_rows(self, text):
        rows = []
        for line in text.splitlines():
            parts = re.split(r'\s{2,}', line.strip())
            if len(parts) >= 5 and parts[0].lower() not in ('group-name', '----------'):
                try:
                    interface_count = int(parts[2])
                except ValueError:
                    continue
                rows.append({'group_name': parts[0], 'status': parts[1].lower(), 'interface_count': interface_count})
        return rows

    def run(self):
        min_count = self.get_threshold_var('min_ifgroup_interface_cnt', default=DEFAULT_MIN_INTERFACE_COUNT, value_type='int')
        bad_keywords = self._split_list(self.get_threshold_var('ifgroup_status_keywords', default=','.join(DEFAULT_BAD_STATUS_KEYWORDS), value_type='str'))
        thresholds = {'min_ifgroup_interface_cnt': min_count, 'ifgroup_status_keywords': bad_keywords}
        stdout, error = self._run_command()
        if error:
            return error

        rows = self._parse_ifgroup_rows(stdout)
        no_interfaces = 'No interfaces in ifgroup' in stdout
        bad_rows = [row for row in rows if row['status'] != 'enabled' or any(keyword in row['status'] for keyword in bad_keywords) or row['interface_count'] < min_count]
        metrics = {'ifgroup_rows': rows, 'bad_ifgroup_rows': bad_rows, 'no_interfaces_message': no_interfaces}
        if not rows or bad_rows or no_interfaces:
            return self.fail('ifgroup 상태 기준 미달', message='ifgroup가 enabled 상태가 아니거나 interface 수 기준을 만족하지 못했습니다.', stdout=stdout, metrics=metrics, thresholds=thresholds)
        return self.ok(metrics=metrics, thresholds=thresholds, reasons='ifgroup가 enabled 상태이고 interface 수 기준을 만족합니다.', message='Path 이중화 점검 정상.')


CHECK_CLASS = Check
