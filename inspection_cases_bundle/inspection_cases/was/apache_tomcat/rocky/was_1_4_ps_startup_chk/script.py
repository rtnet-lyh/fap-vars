# -*- coding: utf-8 -*-

from .common._base import BaseCheck


COMMAND = 'ps -ef | grep tomcat | grep -v grep'
COMMAND_TIMEOUT = 20


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'linux'
    PARAMIKO_REUSE_SESSION = False

    def run(self):
        result = self._run_paramiko_commands(
            [{'command': COMMAND, 'timeout': COMMAND_TIMEOUT}],
            become=True,
            profile='linux',
        )[0]
        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()
        if result.get('rc') != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='Apache Tomcat 기동 프로세스 확인 명령 실행에 실패했습니다.',
                stdout=stdout,
                stderr=stderr,
            )

        lines = [line.strip() for line in stdout.splitlines() if line.strip()]
        tomcat_lines = [
            line for line in lines
            if 'tomcat' in line.lower() and 'grep' not in line.lower()
        ]
        metrics = {
            'tomcat_process_count': len(tomcat_lines),
            'processes': tomcat_lines,
        }
        if not tomcat_lines:
            return self.warn(
                metrics=metrics,
                reasons='Apache Tomcat 기동 프로세스가 확인되지 않습니다.',
                message='Apache Tomcat 프로세스 기동 경고: 프로세스 없음',
            )
        return self.ok(
            metrics=metrics,
            reasons='Apache Tomcat 기동 프로세스가 확인되었습니다.',
            message='Apache Tomcat 프로세스 기동 정상: process_count=%s' % len(tomcat_lines),
        )


CHECK_CLASS = Check
