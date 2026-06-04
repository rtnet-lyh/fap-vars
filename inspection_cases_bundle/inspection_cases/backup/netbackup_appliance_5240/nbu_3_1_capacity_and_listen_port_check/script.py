# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


COMMAND = '/usr/openv/pdde/pdcr/bin/crcontrol --dsstat && netstat -tuln | grep LISTEN'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'    
    PARAMIKO_REUSE_SESSION = True
    PARAMIKO_COMMAND_TIMEOUT = 5 
    PARAMIKO_AUTH_TIMEOUT_SEC = 20  

    def _denied_ports(self):
        raw = self.get_threshold_var('denied_ports', default='', value_type='str')
        return [item.strip() for item in str(raw or '').split(',') if item.strip()]

    def _run_command(self):
        try:
            self.get_elevate_for_aos()
        except Exception as exc:
            return None, self.fail('AOS 권한 상승 실패', message=str(exc))

        result = self._run_paramiko_commands(
            [{'command': COMMAND, 'timeout': 10}],
            
        )[0]
        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()
        if self._is_connection_error(result.get('rc'), stderr):
            return None, self.fail('호스트 연결 실패', message=stderr or 'Paramiko 연결 확인에 실패했습니다.', stderr=stderr)
        if result.get('rc') != 0:
            return None, self.fail('점검 명령 실행 실패', message='용량 및 LISTEN 포트 조회 명령 실행에 실패했습니다.', stdout=stdout, stderr=stderr)
        return stdout, None

    def _parse_usage_percent(self, stdout):
        for line in str(stdout or '').splitlines():
            match = re.match(r'^\s*\S+\s+\S+\s+\S+\s+\S+\s+([0-9.]+)%\s+([0-9.]+)%', line)
            if match:
                return float(match.group(2))
        return None

    def _parse_listen_ports(self, stdout):
        ports = []
        for line in str(stdout or '').splitlines():
            parts = line.split()
            if len(parts) < 4 or 'LISTEN' not in parts:
                continue
            local_address = parts[3]
            port = local_address.rsplit(':', 1)[-1]
            if port.isdigit():
                ports.append(port)
        return ports

    def run(self):
        stdout, error = self._run_command()
        if error:
            return error

        max_usage_percent = self.get_threshold_var('max_usage_percent', default=80, value_type='float')
        denied_ports = self._denied_ports()
        thresholds = {
            'max_usage_percent': max_usage_percent,
            'denied_ports': ','.join(denied_ports),
        }

        usage_percent = self._parse_usage_percent(stdout)
        listen_ports = self._parse_listen_ports(stdout)
        
        if usage_percent is None or not listen_ports:
            return self.fail('용량 또는 포트 출력 파싱 실패', message='Use% 또는 LISTEN 포트 값을 해석하지 못했습니다.', stdout=stdout, thresholds=thresholds)

        denied_found = sorted(set(port for port in listen_ports if port in denied_ports))
        metrics = {
            'usage_percent': usage_percent,
            'listen_port_count': len(listen_ports),
            'listen_ports': listen_ports,
            'denied_ports_found': denied_found,
        }
        if usage_percent > max_usage_percent or denied_found:
            return self.fail(error='Use%가 기준을 초과했거나 금지 포트가 LISTEN 상태입니다.', metrics=metrics, thresholds=thresholds, reasons='Use%가 기준을 초과했거나 금지 포트가 LISTEN 상태입니다.', message='용량/포트 상태 경고: Use%%=%s, 금지 포트=%s.' % (usage_percent, ','.join(denied_found) or '없음'))
        return self.ok(metrics=metrics, thresholds=thresholds, reasons='Use%가 기준 이하이고 금지 포트가 LISTEN 상태가 아닙니다.', message='용량 및 LISTEN 포트 점검 정상')


CHECK_CLASS = Check