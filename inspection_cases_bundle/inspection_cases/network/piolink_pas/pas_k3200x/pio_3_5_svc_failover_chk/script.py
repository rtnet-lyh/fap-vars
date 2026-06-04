# -*- coding: utf-8 -*-

from .common._base import BaseCheck


COMMAND = 'show failover'


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

    def _parse_vrrp_rows(self, text):
        rows = []
        for line in (text or '').splitlines():
            parts = line.split()
            if len(parts) < 4 or not parts[0].isdigit():
                continue
            running = parts[2].lower()
            status = parts[3].lower()
            rows.append({
                'vrid': parts[0],
                'mode': parts[1],
                'running': running,
                'status': status,
                'raw': line.strip(),
            })
        return rows

    def run(self):
        stdout, error = self._run_command()
        if error:
            return error

        vrrp_rows = self._parse_vrrp_rows(stdout)
        if not vrrp_rows:
            return self.fail('VRRP 상태 파싱 실패', message='show failover 출력에서 VRRP 행을 찾지 못했습니다.', stdout=stdout)

        invalid_rows = [
            item for item in vrrp_rows
            if item['running'] not in ('master', 'backup') or item['status'] != 'enable'
        ]
        metrics = {
            'vrrp_count': len(vrrp_rows),
            'invalid_vrrp_rows': invalid_rows,
            'vrrp_rows': vrrp_rows,
        }
        if invalid_rows:
            return self.fail(error='VRRP Running 또는 Status 기준을 만족하지 않는 행이 있습니다.', metrics=metrics, thresholds={}, reasons='VRRP Running 또는 Status 기준을 만족하지 않는 행이 있습니다.', message=f'Failover 상태 경고: 비정상 VRRP {len(invalid_rows)}개.')
        return self.ok(metrics=metrics, thresholds={}, reasons='VRRP Running이 master/backup이고 Status가 enable입니다.', message=f'Failover 상태 점검 정상: VRRP {len(vrrp_rows)}개.')


CHECK_CLASS = Check
