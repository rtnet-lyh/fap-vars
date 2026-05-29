# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


COMMAND_ERROR_MARKERS = ('syntax error', 'unknown command', 'invalid command', 'command not found')
COMMAND = 'enclosure show powersupply'
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

    def _parse_power_statuses(self, text):
        statuses = []
        for line in text.splitlines():
            match = re.match(r'^(\d+)\s+(Power module\s+\S+)\s+(\S+)\s*$', line.strip(), re.IGNORECASE)
            if match:
                statuses.append({'enclosure': match.group(1), 'description': match.group(2), 'status': match.group(3)})
        return statuses

    def run(self):
        stdout, error = self._run_command()
        if error:
            return error

        statuses = self._parse_power_statuses(stdout)
        bad_statuses = [item for item in statuses if item['status'].lower() not in OK_STATUSES]
        metrics = {'power_status_count': len(statuses), 'bad_power_statuses': bad_statuses, 'power_statuses': statuses}
        thresholds = {'valid_statuses': list(OK_STATUSES)}
        if not statuses or bad_statuses:
            return self.fail('Power Supply 상태 기준 미달', message='Power module Status가 없거나 OK가 아닌 값이 확인되었습니다.', stdout=stdout, metrics=metrics, thresholds=thresholds)
        return self.ok(metrics=metrics, thresholds=thresholds, reasons='Power module Status가 모두 OK입니다.', message='전원공급 장치 점검 정상.')


CHECK_CLASS = Check
