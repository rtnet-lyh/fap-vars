# -*- coding: utf-8 -*-

from .common._base import BaseCheck


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'linux'
    PARAMIKO_REUSE_SESSION = False

    DEFAULT_IP_ADDR = '127.0.0.1'
    DEFAULT_SERVICE_PORT = 9080
    COMMAND_TIMEOUT = 10

    def run(self):
        ip_addr = self.get_host_var(key='ip_addr')
        webtob_service_port = self.get_host_var(key='webtob_service_port')

        if not ip_addr:
            ip_addr = self.get_threshold_var(
                'ip_addr', 
                default=self.DEFAULT_IP_ADDR, 
                value_type='str'
            ).strip()

        if not webtob_service_port:
            service_port = self.get_threshold_var(
                'webtob_service_port',
                default=self.DEFAULT_SERVICE_PORT,
                value_type='int',
            )

        command = 'echo quit | telnet %s %s' % (ip_addr, service_port)

        result = self._run_paramiko_commands(
            [{'command': command, 'timeout': self.COMMAND_TIMEOUT}],
            become=True,
            profile='linux',
        )[0]

        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()
        if result.get('rc') != 0:
            return self.fail(
                'telnet 명령 실행 실패',
                message='WebtoB 서비스 포트 접속을 확인하지 못했습니다.',
                stdout=stdout,
                stderr=stderr,
            )

        connected = 'Connected to' in stdout
        metrics = {
            'ip_addr': ip_addr,
            'webtob_service_port': service_port,
            'connected': connected,
        }
        thresholds = {
            'ip_addr': ip_addr,
            'webtob_service_port': service_port,
            'success_marker': 'Connected to',
        }

        if not connected:
            return self.warn(
                metrics=metrics,
                thresholds=thresholds,
                reasons='telnet 출력에서 Connected to 문구를 찾지 못했습니다.',
                message='WebtoB 서비스 포트 접속 경고: %s:%s 연결 확인 실패' % (
                    ip_addr,
                    service_port,
                ),
            )

        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='telnet 접속 출력에서 Connected to 문구를 확인했습니다.',
            message='WebtoB 서비스 포트 접속 정상: %s:%s' % (
                ip_addr,
                service_port,
            ),
        )


CHECK_CLASS = Check
