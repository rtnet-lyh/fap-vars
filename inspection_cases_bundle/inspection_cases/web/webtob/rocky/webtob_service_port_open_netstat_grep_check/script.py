# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'linux'
    PARAMIKO_REUSE_SESSION = False

    DEFAULT_SERVICE_PORT = 9080
    DEFAULT_ALLOW_STATE = 'LISTEN'
    COMMAND_TIMEOUT = 10

    def _parse_netstat_rows(self, stdout):
        rows = []
        for line in str(stdout or '').splitlines():
            parts = re.split(r'\s+', line.strip())
            if len(parts) < 6 or parts[0] not in ('tcp', 'tcp6'):
                continue
            rows.append({
                'protocol': parts[0],
                'recv_q': parts[1],
                'send_q': parts[2],
                'local_address': parts[3],
                'foreign_address': parts[4],
                'state': parts[5],
            })
        return rows

    def run(self):
        service_port = self.get_host_var(key='webtob_service_port')

        if not service_port:
            service_port = self.get_threshold_var(
                'webtob_service_port',
                default=self.DEFAULT_SERVICE_PORT,
                value_type='int',
            )
            
        allow_state = str(
            self.get_threshold_var('allow_state', default=self.DEFAULT_ALLOW_STATE, value_type='str') or ''
        ).strip().upper() or self.DEFAULT_ALLOW_STATE
        command = 'netstat -an | grep %s' % service_port

        result = self._run_paramiko_commands(
            [{'command': command, 'timeout': self.COMMAND_TIMEOUT}],
            become=True,
            profile='linux',
        )[0]

        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()
        if result.get('rc') != 0:
            return self.fail(
                'netstat 명령 실행 실패',
                message='WebtoB 서비스 포트 상태를 확인하지 못했습니다.',
                stdout=stdout,
                stderr=stderr,
            )

        rows = self._parse_netstat_rows(stdout)
        if not rows:
            return self.fail(
                '서비스 포트 정보 없음',
                message='netstat 출력에서 대상 포트를 찾지 못했습니다.',
                stdout=stdout,
                stderr=stderr,
            )

        listening_rows = [
            row for row in rows
            if row['protocol'] in ('tcp', 'tcp6') and row['state'].upper() == allow_state
        ]
        metrics = {
            'webtob_service_port': service_port,
            'connection_count': len(rows),
            'listen_count': len(listening_rows),
            'connections': rows,
        }
        thresholds = {
            'webtob_service_port': service_port,
            'allow_state': allow_state,
            'allow_protocols': ['tcp', 'tcp6'],
        }

        if not listening_rows:
            return self.warn(
                metrics=metrics,
                thresholds=thresholds,
                reasons='대상 포트가 LISTEN 상태가 아닙니다.',
                message='WebtoB 서비스 포트 오픈 경고: port=%s, listen_count=0' % service_port,
            )

        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='대상 포트가 tcp LISTEN 상태입니다.',
            message='WebtoB 서비스 포트 오픈 정상: port=%s, listen_count=%s' % (
                service_port,
                len(listening_rows),
            ),
        )


CHECK_CLASS = Check
