# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


COMMAND_ERROR_MARKERS = ('syntax error', 'unknown command', 'invalid command', 'unknown keyword', 'missing argument')
COMMAND = 'show chassis environment'


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

    def _parse_environment_statuses(self, text):
        statuses = []
        for line in (text or '').splitlines():
            stripped = line.rstrip()
            if not stripped or stripped.startswith('Class ') or set(stripped.strip()) <= {'-'}:
                continue
            match = re.match(r'^\s*(?P<item>.+?)\s{2,}(?P<status>[A-Za-z][A-Za-z_-]*)(?:\s{2,}.*)?$', stripped)
            if not match:
                continue
            status = match.group('status')
            if status.lower() not in ('status', 'measurement'):
                statuses.append({'item': match.group('item').strip(), 'status': status})
        return statuses

    def run(self):
        stdout, error = self._run_command(COMMAND)
        if error:
            return error

        statuses = self._parse_environment_statuses(stdout)
        if not statuses:
            return self.fail('환경 상태 파싱 실패', message='show chassis environment 출력에서 Status 값을 찾지 못했습니다.', stdout=stdout, thresholds={})
        bad_statuses = [item for item in statuses if item['status'].upper() != 'OK']
        metrics = {'status_count': len(statuses), 'bad_statuses': bad_statuses, 'statuses': statuses}
        if bad_statuses:
            return self.fail('환경 상태 기준 미달', message=f'OK가 아닌 하드웨어 Status가 {len(bad_statuses)}개 있습니다.', stdout=stdout, metrics=metrics, thresholds={})
        return self.ok(metrics=metrics, thresholds={}, reasons='하드웨어 Status 값이 모두 OK입니다.', message='전원/FAN 등 환경 상태 점검 정상.')


CHECK_CLASS = Check
