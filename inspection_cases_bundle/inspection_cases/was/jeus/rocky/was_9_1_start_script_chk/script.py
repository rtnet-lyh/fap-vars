# -*- coding: utf-8 -*-

from .common._base import BaseCheck


COMMAND = 'stat /home/exTMS/tmax/jeus/bin/startDomainAdminServer'


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
        metrics = {'has_file': 'File:' in stdout, 'has_access': 'Access:' in stdout, 'has_modify': 'Modify:' in stdout, 'has_change': 'Change:' in stdout}
        thresholds = {'required_fields': ['File', 'Access', 'Modify', 'Change']}
        if not all(metrics.values()):
            return self.fail('stat 출력 파싱 실패', message='stat 출력에서 File/Access/Modify/Change 값을 모두 확인하지 못했습니다.', stdout=stdout, metrics=metrics, thresholds=thresholds)
        return self.ok(metrics=metrics, thresholds=thresholds, reasons='기동 스크립트 stat 정보를 확인했습니다.', message='JEUS 기동 스크립트 stat 확인 정상')


CHECK_CLASS = Check
