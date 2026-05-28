# -*- coding: utf-8 -*-

from .common._base import BaseCheck


COMMAND = "bpdbjobs | awk 'NR==1 || $2==\"Backup\"'"
STATE_VALUES = {'Active', 'Done', 'Queued', 'Requeued', 'Restarted', 'Suspended', 'Waiting'}


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
            return None, self.fail('점검 명령 실행 실패', message='Backup 작업 상태 명령 실행에 실패했습니다.', stdout=stdout, stderr=stderr)
        return stdout, None

    def _parse_jobs(self, stdout):
        rows = []
        for line in str(stdout or '').splitlines():
            tokens = line.split()
            if not tokens or not tokens[0].isdigit():
                continue
            state_idx = next((idx for idx, token in enumerate(tokens[1:], 1) if token in STATE_VALUES), -1)
            if state_idx < 2 or state_idx + 1 >= len(tokens):
                continue
            rows.append({
                'job_id': tokens[0],
                'type': ' '.join(tokens[1:state_idx]),
                'state': tokens[state_idx],
                'status_code': tokens[state_idx + 1],
                'raw': line.strip(),
            })
        return rows

    def run(self):
        stdout, error = self._run_command()
        if error:
            return error

        rows = self._parse_jobs(stdout)
        if not rows:
            return self.fail('Backup 출력 파싱 실패', message='bpdbjobs 출력에서 Backup 작업 행을 찾지 못했습니다.', stdout=stdout)

        invalid_rows = [row for row in rows if row['state'] != 'Done' or row['status_code'] != '0']
        metrics = {
            'backup_job_count': len(rows),
            'invalid_job_count': len(invalid_rows),
            'invalid_jobs': invalid_rows,
        }
        thresholds = {'required_state': 'Done', 'required_status_code': '0'}
        if invalid_rows:
            return self.warn(metrics=metrics, thresholds=thresholds, reasons='Backup 작업 중 Done/0 기준을 만족하지 않는 행이 있습니다.', message='백업 작업 상태 경고: 비정상 작업 %s건.' % len(invalid_rows))
        return self.ok(metrics=metrics, thresholds=thresholds, reasons='모든 Backup 작업의 State가 Done이고 Statu 값이 0입니다.', message='백업 작업 상태 점검 정상')


CHECK_CLASS = Check
