# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


COMMAND = '/opt/MegaRAID/storcli/storcli64 /c0 /eall /sall show'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'linux'
    PARAMIKO_REUSE_SESSION = True
    PARAMIKO_AUTH_METHOD = 'password'
    PARAMIKO_AUTH_TIMEOUT_SEC = 20
    COMMAND_TIMEOUT = 5

    def _paramiko_sendline(self, channel, text, delay=0):
        if self.ctx.get('paramiko_client_factory'):
            delay = 0
        return super()._paramiko_sendline(channel, text, delay=delay)

    def _paramiko_session_alive(self, session):
        if self.ctx.get('paramiko_client_factory') and isinstance(session, dict):
            channel = session.get('channel')
            return channel is not None and not getattr(channel, 'closed', False)
        return super()._paramiko_session_alive(session)

    def _allowed_states(self):
        raw = self.get_threshold_var('disk_state_value', default='Onln,DHS', value_type='str')
        return [item.strip() for item in str(raw or '').split(',') if item.strip()]

    def _run_command(self):
        BaseCheck.PARAMIKO_IS_ELEVATED = False
        BaseCheck.PARAMIKO_ELEVATE_FAILED = False
        try:
            self.get_elevate_for_aos()
        except Exception as exc:
            return None, self.fail('AOS 권한 상승 실패', message=str(exc))

        result = self._run_paramiko_commands(
            [{'command': COMMAND, 'timeout': self.COMMAND_TIMEOUT}],
            profile='linux',
        )[0]
        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()
        if self._is_connection_error(result.get('rc'), stderr):
            return None, self.fail('호스트 연결 실패', message=stderr or 'Paramiko 연결 확인에 실패했습니다.', stderr=stderr)
        if result.get('rc') != 0:
            return None, self.fail('점검 명령 실행 실패', message='물리 디스크 상태 조회 명령 실행에 실패했습니다.', stdout=stdout, stderr=stderr)
        return stdout, None

    def _parse_disk_rows(self, stdout):
        rows = []
        for line in str(stdout or '').splitlines():
            parts = line.split()
            if len(parts) < 3 or not re.match(r'^\d+:\d+$', parts[0]):
                continue
            rows.append({
                'eid_slot': parts[0],
                'did': parts[1],
                'state': parts[2],
                'raw': line.strip(),
            })
        return rows

    def run(self):
        stdout, error = self._run_command()
        if error:
            return error

        allowed_states = self._allowed_states()
        rows = self._parse_disk_rows(stdout)
        thresholds = {'disk_state_value': ','.join(allowed_states)}
        if not rows:
            return self.fail('storcli 출력 파싱 실패', message='Drive Information 출력에서 물리 디스크 행을 찾지 못했습니다.', stdout=stdout, thresholds=thresholds)

        invalid_rows = [row for row in rows if row['state'] not in allowed_states]
        metrics = {
            'disk_count': len(rows),
            'invalid_disk_count': len(invalid_rows),
            'invalid_disks': invalid_rows,
        }
        if invalid_rows:
            return self.warn(metrics=metrics, thresholds=thresholds, reasons='물리 디스크 State 값이 기준을 만족하지 않는 행이 있습니다.', message='디스크 Fault 상태 경고: 비정상 디스크 %s개.' % len(invalid_rows))
        return self.ok(metrics=metrics, thresholds=thresholds, reasons='모든 물리 디스크 State 값이 기준을 만족합니다.', message='디스크 Fault 상태 점검 정상')


CHECK_CLASS = Check
