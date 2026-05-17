# -*- coding: utf-8 -*-

from .common._base import BaseCheck


COMMAND = '/home/exTMS/tmax/jeus/bin/jeusctl status'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'linux'
    PARAMIKO_REUSE_SESSION = False

    COMMAND_TIMEOUT = 20

    def _run_jeus_command(self):
        result = self._run_paramiko_commands(
            [{'command': COMMAND, 'timeout': self.COMMAND_TIMEOUT}],
            become=True,
            profile='linux',
        )[0]
        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()
        if result.get('rc') != 0:
            return stdout, stderr, self.fail(
                '점검 명령 실행 실패',
                message='JEUS 점검 명령 실행에 실패했습니다.',
                stdout=stdout,
                stderr=stderr,
            )
        return stdout, stderr, None

    def run(self):
        stdout, _stderr, error = self._run_jeus_command()
        if error:
            return error
        lines = [line.strip() for line in stdout.splitlines() if line.strip()]
        if not lines:
            return self.fail('JEUS 상태 정보 없음', message='jeusctl status 출력이 비어 있습니다.', stdout=stdout)
        running_lines = [line for line in lines if 'RUNNING' in line.upper()]
        abnormal_lines = [line for line in lines if any(word in line.upper() for word in ('STOPPED', 'DOWN', 'FAILED'))]
        metrics = {'status_lines': lines, 'running_count': len(running_lines), 'abnormal_count': len(abnormal_lines), 'abnormal_lines': abnormal_lines}
        thresholds = {'required_status': 'RUNNING'}
        if not running_lines or abnormal_lines:
            return self.warn(metrics=metrics, thresholds=thresholds, reasons='RUNNING이 아닌 JEUS 상태가 있습니다.', message='JEUS 기동 상태 경고: running=%s, abnormal=%s' % (len(running_lines), len(abnormal_lines)))
        return self.ok(metrics=metrics, thresholds=thresholds, reasons='JEUS 상태가 RUNNING입니다.', message='JEUS 기동 상태 정상: running=%s' % len(running_lines))


CHECK_CLASS = Check
