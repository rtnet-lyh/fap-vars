# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


COMMAND = 'show stp'
GLOBAL_STATUS_RE = re.compile(r'^\s*Status\s*:\s*(\S+)', re.IGNORECASE | re.MULTILINE)


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

    def _parse_ports(self, text):
        ports = []
        for line in (text or '').splitlines():
            parts = line.split()
            if len(parts) < 4 or not parts[0].isdigit():
                continue
            status = parts[1].lower()
            link = parts[2].lower()
            if status not in ('enable', 'disable') or link not in ('up', 'down'):
                continue
            ports.append({'port': parts[0], 'status': status, 'link': link, 'used': status == 'enable'})
        return ports

    def run(self):
        stdout, error = self._run_command()
        if error:
            return error

        ports = self._parse_ports(stdout)
        global_match = GLOBAL_STATUS_RE.search(stdout)
        global_status = global_match.group(1).lower() if global_match else ''
        if not ports:
            return self.fail('STP 포트 파싱 실패', message='show stp 출력에서 포트 상태 행을 찾지 못했습니다.', stdout=stdout, metrics={'global_status': global_status})

        used_ports = [item for item in ports if item['used']]
        down_used_ports = [item for item in used_ports if item['link'] != 'up']
        metrics = {
            'global_status': global_status,
            'port_count': len(ports),
            'used_port_count': len(used_ports),
            'down_used_ports': down_used_ports,
            'used_ports': used_ports,
        }
        if not used_ports:
            return self.warn(metrics=metrics, thresholds={}, reasons='STP 사용 포트를 찾지 못했습니다.', message='STP 상태 경고: 사용 포트가 없습니다.')
        if down_used_ports:
            return self.warn(metrics=metrics, thresholds={}, reasons='사용 포트 중 Link가 up이 아닌 포트가 있습니다.', message=f'STP 상태 경고: Link down 사용 포트 {len(down_used_ports)}개.')
        return self.ok(metrics=metrics, thresholds={}, reasons='STP 전역 Status는 참고값으로 기록하고, 사용 포트 Link가 up인지 확인했습니다.', message=f'STP 상태 점검 정상: 사용 포트 {len(used_ports)}개.')


CHECK_CLASS = Check
