# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


COMMAND_ERROR_MARKERS = ('syntax error', 'unknown command', 'invalid command', 'command not found')
COMMAND = 'enclosure show all'
OK_STATUSES = ('ok',)


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

    def _parse_enclosure_statuses(self, text):
        statuses = []
        section = ''
        target_sections = {'Fans', 'Temperature', 'Power Supply', 'Controller', 'NVRAM Batteries'}
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.rstrip(':') in target_sections:
                section = stripped.rstrip(':')
                continue
            if stripped.endswith(':'):
                section = ''
                continue
            if not section or not stripped or stripped.startswith(('Description', 'Card', 'Status')):
                continue
            compact = stripped.replace(' ', '')
            if compact and set(compact) <= {'-'}:
                continue
            if section == 'NVRAM Batteries' and re.match(r'^\d+\s+\d+\s+\S+', stripped):
                parts = stripped.split()
                statuses.append({'section': section, 'item': 'card %s battery %s' % (parts[0], parts[1]), 'status': parts[2]})
                continue
            if section == 'Controller' and stripped.lower().startswith('status'):
                parts = stripped.split()
                if len(parts) >= 2:
                    statuses.append({'section': section, 'item': 'Controller', 'status': parts[-1]})
                continue
            if section in ('Fans', 'Temperature', 'Power Supply'):
                parts = re.split(r'\s{2,}', stripped)
                if len(parts) >= 2:
                    status = parts[-1].strip()
                    if status == '-' or not re.match(r'^[A-Za-z_-]+$', status):
                        continue
                    statuses.append({'section': section, 'item': parts[0], 'status': status})
        return statuses

    def run(self):
        stdout, error = self._run_command()
        if error:
            return error

        statuses = self._parse_enclosure_statuses(stdout)
        bad_statuses = [item for item in statuses if item['status'].lower() not in OK_STATUSES]
        metrics = {'enclosure_status_count': len(statuses), 'bad_enclosure_statuses': bad_statuses, 'enclosure_statuses': statuses}
        thresholds = {'valid_statuses': list(OK_STATUSES)}
        if not statuses or bad_statuses:
            return self.fail('Enclosure HW 상태 기준 미달', message='관련 Status가 없거나 OK/ok가 아닌 값이 확인되었습니다.', stdout=stdout, metrics=metrics, thresholds=thresholds)
        return self.ok(metrics=metrics, thresholds=thresholds, reasons='관련 Enclosure HW Status가 모두 OK/ok입니다.', message='Enclosure HW 상태 점검 정상.')


CHECK_CLASS = Check
