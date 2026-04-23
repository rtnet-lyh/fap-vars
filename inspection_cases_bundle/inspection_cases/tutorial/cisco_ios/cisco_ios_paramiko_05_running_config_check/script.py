# -*- coding: utf-8 -*-

from .common._base import BaseCheck


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
        min_config_line_count = self.get_threshold_var(
            'min_config_line_count',
            default=20,
            value_type='int',
        )
        results, error = self._run_with_enable([
            {
                'command': 'terminal length 0',
            },
            {
                'command': 'show running-config',
                'timeout': 20,
            },
        ])
        if error:
            return error

        config_output = (results[3].get('stdout') or '').strip()
        config_lines = [line.rstrip() for line in config_output.splitlines() if line.strip()]
        hostname_line = next((line.strip() for line in config_lines if line.strip().startswith('hostname ')), '')
        hostname = hostname_line.split(None, 1)[1].strip() if hostname_line else ''

        if len(config_lines) < min_config_line_count:
            return self.fail(
                '설정 라인 수 기준 미달',
                message=(
                    f'show running-config 결과 라인 수가 기준 미만입니다: '
                    f'{len(config_lines)}줄 (기준 {min_config_line_count}줄 이상)'
                ),
                stdout=config_output,
            )

        if not hostname:
            return self.fail(
                'hostname 라인 없음',
                message='show running-config 결과에서 hostname 라인을 찾지 못했습니다.',
                stdout=config_output,
            )

        return self.ok(
            metrics={
                'commands': [item.get('display_command') or item.get('command') for item in results],
                'config_line_count': len(config_lines),
                'hostname': hostname,
            },
            thresholds={
                'min_config_line_count': min_config_line_count,
            },
            reasons='긴 running-config 출력과 hostname을 정상 수집했습니다.',
            message=(
                '_run_paramiko_commands 고급 예제가 정상 수행되었습니다. '
                f'hostname={hostname}, config_line_count={len(config_lines)}'
            ),
        )


CHECK_CLASS = Check
