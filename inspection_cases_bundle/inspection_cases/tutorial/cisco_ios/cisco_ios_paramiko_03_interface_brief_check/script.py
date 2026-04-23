# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


INTERFACE_LINE_PATTERN = re.compile(
    r'^(?P<interface>\S+)\s+\S+\s+\S+\s+\S+\s+'
    r'(?P<status>administratively down|up|down)\s+'
    r'(?P<protocol>up|down)\s*$',
    re.IGNORECASE,
)


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'cisco_ios'

    def _run_with_enable(self, command_items):
        enable_password = str(self.get_connection_value('en_password', '') or '')
        if not enable_password:
            return None, self.fail(
                'enable 비밀번호 없음',
                message='connection credential에 en_password가 필요합니다.',
            )

        results = self._run_paramiko_commands([
            {
                'command': 'enable',
                'ignore_prompt': True,
            },
            {
                'command': enable_password,
                'hide_command': True,
            },
        ] + list(command_items))

        failed = [
            item for item in results
            if item.get('rc') != 0 and not (item.get('command') == 'enable' and item.get('timed_out'))
        ]
        if failed:
            first = failed[0]
            display_command = first.get('display_command') or first.get('command')
            return None, self.fail(
                '점검 명령 실행 실패',
                message=f'{display_command} 명령 실행에 실패했습니다.',
                stdout=(first.get('stdout') or '').strip(),
                stderr=(first.get('stderr') or '').strip(),
            )

        if len(results) < 2:
            return None, self.fail(
                'enable 모드 진입 실패',
                message='enable 명령 처리 결과가 부족합니다.',
            )

        enable_prompt = str(results[1].get('prompt') or '').strip()
        if not enable_prompt.endswith('#'):
            return None, self.fail(
                'enable 모드 진입 실패',
                message='enable 비밀번호 입력 후 privileged prompt(#)를 확인하지 못했습니다.',
                stdout=(results[1].get('stdout') or '').strip(),
                stderr=(results[1].get('stderr') or '').strip(),
            )

        return results, None

    def run(self):
        min_up_interface_count = self.get_threshold_var(
            'min_up_interface_count',
            default=1,
            value_type='int',
        )
        results, error = self._run_with_enable([
            {
                'command': 'terminal length 0',
            },
            {
                'command': 'show ip interface brief',
            },
        ])
        if error:
            return error

        interface_output = (results[3].get('stdout') or '').strip()
        interfaces = []
        for raw_line in interface_output.splitlines():
            line = raw_line.rstrip()
            if not line or line.lower().startswith('interface '):
                continue
            match = INTERFACE_LINE_PATTERN.match(line)
            if not match:
                continue
            interfaces.append({
                'interface': match.group('interface'),
                'status': match.group('status').lower(),
                'protocol': match.group('protocol').lower(),
            })

        if not interfaces:
            return self.fail(
                '출력 파싱 실패',
                message='show ip interface brief 결과에서 인터페이스 정보를 해석하지 못했습니다.',
                stdout=interface_output,
            )

        up_interfaces = [
            item['interface']
            for item in interfaces
            if item['status'] == 'up' and item['protocol'] == 'up'
        ]

        if len(up_interfaces) < min_up_interface_count:
            return self.fail(
                'UP 인터페이스 수 기준 미달',
                message=(
                    f'UP 상태 인터페이스 수가 기준 미만입니다: '
                    f'{len(up_interfaces)}개 (기준 {min_up_interface_count}개 이상)'
                ),
                stdout=interface_output,
            )

        return self.ok(
            metrics={
                'commands': [item.get('display_command') or item.get('command') for item in results],
                'interface_count': len(interfaces),
                'up_interface_count': len(up_interfaces),
                'up_interfaces': up_interfaces,
                'interfaces': interfaces,
            },
            thresholds={
                'min_up_interface_count': min_up_interface_count,
            },
            reasons='show ip interface brief 결과를 정상 파싱했습니다.',
            message=(
                '_run_paramiko_commands 파싱 예제가 정상 수행되었습니다. '
                f'up_interface_count={len(up_interfaces)}'
            ),
        )


CHECK_CLASS = Check
