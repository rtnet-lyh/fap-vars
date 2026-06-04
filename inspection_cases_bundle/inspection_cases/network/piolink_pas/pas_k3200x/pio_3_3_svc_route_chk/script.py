# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


COMMAND = 'show route'
DEFAULT_GATEWAY_RE = re.compile(r'Default-Gateway\s*:\s*(\S+)')
DESTINATION_RE = re.compile(r'^\s*(?P<destination>\d+(?:\.\d+){3}/\d+)\s+\S+\s+(?P<interface>\S+)\s*$')


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'generic_network'
    PARAMIKO_REUSE_SESSION = True

    def _run_command(self):
        results = self._run_paramiko_commands([COMMAND], profile=self.PARAMIKO_PROFILE)
        if not results:
            return None, self.fail('점검 명령 실행 실패', message='Paramiko 명령 실행 결과가 비어 있습니다.')
        result = results[0]
        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()
        if result.get('rc') != 0:
            return None, self.fail('점검 명령 실행 실패', message=f'{COMMAND} 명령 실행에 실패했습니다.', stdout=stdout, stderr=stderr)
        return stdout, None

    def _parse_routes(self, text):
        routes = []
        for line in (text or '').splitlines():
            match = DESTINATION_RE.match(line)
            if match:
                routes.append(match.groupdict())
        gateway_match = DEFAULT_GATEWAY_RE.search(text or '')
        return gateway_match.group(1) if gateway_match else '', routes

    def run(self):
        stdout, error = self._run_command()
        if error:
            return error

        default_gateway, routes = self._parse_routes(stdout)
        if 'ROUTE' not in stdout and not routes and not default_gateway:
            return self.fail('라우팅 정보 파싱 실패', message='show route 출력에서 ROUTE 정보를 찾지 못했습니다.', stdout=stdout)

        missing = []
        if not default_gateway:
            missing.append('Default-Gateway')
        if not routes:
            missing.append('route destination/interface')
        metrics = {
            'default_gateway': default_gateway,
            'route_count': len(routes),
            'routes': routes,
            'missing': missing,
        }
        if missing:
            return self.fail(error="Default-Gateway 또는 route destination/interface 정보가 없습니다.", metrics=metrics, thresholds={}, reasons='Default-Gateway 또는 route destination/interface 정보가 없습니다.', message='라우팅 Table 상태 경고: ' + ', '.join(missing))
        return self.ok(metrics=metrics, thresholds={}, reasons='Default-Gateway 및 route destination/interface 정보가 존재합니다.', message=f'라우팅 Table 상태 점검 정상: route {len(routes)}개.')


CHECK_CLASS = Check
