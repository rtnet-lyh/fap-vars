# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


COMMAND = 'show interface status'
ROW_RE = re.compile(
    r'^(?P<port>\S+)\s+(?P<name>.*?)(?P<status>connected|notconnect|disabled|err-disabled|inactive|suspended)'
    r'\s+(?P<vlan>\S+)\s+(?P<duplex>\S+)\s+(?P<speed>\S+)\s+(?P<type>.+)$',
    re.IGNORECASE,
)


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'cisco_ios'
    PARAMIKO_REUSE_SESSION = True

    def _set_enable_password(self):
        data = self.get_connection_credential_data()
        for key in ('en_password', 'become_password'):
            value = self.get_connection_value(key, None)
            if value not in (None, ''):
                if isinstance(data, dict) and not data.get('en_password'):
                    data['en_password'] = str(value)
                return True
            value = self.get_application_credential_value(key, None)
            if value not in (None, ''):
                if isinstance(data, dict) and not data.get('en_password'):
                    data['en_password'] = str(value)
                return True
        return False

    def _run_command(self):
        commands = [
            {'command': 'terminal length 0'},
            {'command': COMMAND},
        ]
        results = self._run_paramiko_commands(commands, enable_mode=self._set_enable_password())
        failed = [item for item in results if item.get('rc') != 0]
        if failed:
            first = failed[0]
            command = first.get('display_command') or first.get('command')
            return None, self.fail(
                '점검 명령 실행 실패',
                message=f'{command} 명령 실행에 실패했습니다.',
                stdout=(first.get('stdout') or '').strip(),
                stderr=(first.get('stderr') or '').strip(),
            )
        return (results[-1].get('stdout') or '').strip(), None

    def _parse_rows(self, text):
        rows = []
        for line in (text or '').splitlines():
            match = ROW_RE.match(line.rstrip())
            if not match:
                continue
            rows.append({
                'port': match.group('port'),
                'name': match.group('name').strip(),
                'status': match.group('status').lower(),
                'vlan': match.group('vlan'),
                'duplex': match.group('duplex').lower(),
                'speed': match.group('speed').lower(),
                'type': match.group('type').strip(),
            })
        return rows

    def run(self):
        stdout, error = self._run_command()
        if error:
            return error

        rows = self._parse_rows(stdout)
        if not rows:
            return self.fail(
                '인터페이스 상태 파싱 실패',
                message='show interface status 출력에서 포트 상태를 찾지 못했습니다.',
                stdout=stdout,
            )

        targets = [row for row in rows if row['name']]
        bad = []
        for row in targets:
            negotiated_bad = row['status'] == 'connected' and (
                row['duplex'] in ('auto', 'a-auto') or row['speed'] in ('auto', 'a-auto')
            )
            if row['status'] != 'connected' or negotiated_bad:
                bad.append(row)

        metrics = {
            'interface_count': len(rows),
            'named_interface_count': len(targets),
            'bad_interfaces': bad,
            'named_interfaces': targets,
        }
        if bad:
            return self.warn(
                metrics=metrics,
                thresholds={},
                reasons='이름이 지정된 운영 대상 포트 중 connected 상태가 아닌 포트가 있습니다.',
                message=f'인터페이스 상태 경고: 비정상 운영 대상 포트 {len(bad)}개.',
            )
        return self.ok(
            metrics=metrics,
            thresholds={},
            reasons='이름이 지정된 운영 대상 포트가 모두 connected 상태입니다.',
            message=f'인터페이스 상태 점검 정상: 운영 대상 포트 {len(targets)}개.',
        )


CHECK_CLASS = Check
