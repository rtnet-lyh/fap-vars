# -*- coding: utf-8 -*-

from .common._base import BaseCheck


# COMMAND = '/home/exTMS/tmax/jeus/bin/jeusctl status'
COMMAND = 'ps -ef | grep "{java_name}" | grep "{jeus_name}" | grep -v grep'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'linux'
    PARAMIKO_REUSE_SESSION = False

    COMMAND_TIMEOUT = 20

    def _run_jeus_command(self):
        java_name = self.get_threshold_var(
            key='java_name',
            default='java',
            value_type='str',
        )

        jeus_name = self.get_threshold_var(
            key='jeus_name',
            default='jeus',
            value_type='str',
        )

        command = COMMAND.format(
            java_name=java_name,
            jeus_name=jeus_name,
        )
        
        result = self._run_paramiko_commands(
            [{'command': command, 'timeout': self.COMMAND_TIMEOUT}],
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
        
        metrics = {'output': lines, 'output_count': len(lines)}        
        
        return self.ok(
            metrics=metrics, 
            reasons='JEUS 프로세스 정보 조회 확인', 
            message='JEUS 프로세스 정보 조회 확인',
        )

CHECK_CLASS = Check
