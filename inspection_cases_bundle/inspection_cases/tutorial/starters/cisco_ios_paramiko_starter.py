# -*- coding: utf-8 -*-
# Cisco IOS UI starter template
# 1. COMMAND_ITEMS의 show 명령을 점검 목적에 맞게 먼저 수정한다.
# 2. run() 안에서는 self._run_paramiko_commands(...)로 명령 배열을 실행한다.
# 3. 마지막에는 self.ok(...) 또는 self.fail(...) 중 하나를 반환한다.

from .common._base import BaseCheck


# Step 1. 가장 먼저 이 명령 배열을 바꾼다.
COMMAND_ITEMS = [
    # 긴 출력이 필요하면 아래 예시를 주석 해제한다.
    # {'command': 'terminal length 0'},
    {'command': 'show clock'},
]


class Check(BaseCheck):
    # Step 2. Cisco IOS 기본 연결 방식은 paramiko interactive shell 이다.
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'cisco_ios'

    def run(self):
        # Step 3. threshold가 필요하면 아래 패턴을 주석 해제해서 사용한다.
        # min_up_interface_count = self.get_threshold_var(
        #     'min_up_interface_count',
        #     default=1,
        #     value_type='int',
        # )

        # enable 모드가 필요한 장비라면 아래 두 줄을 COMMAND_ITEMS 앞에 붙이는 패턴을 사용한다.
        # enable_password = str(self.get_connection_value('en_password', '') or '')
        # command_items = [
        #     {'command': 'enable', 'ignore_prompt': True},
        #     {'command': enable_password, 'hide_command': True},
        # ] + list(COMMAND_ITEMS)

        # Step 4. 기본 예시는 show 계열 명령만 바로 실행한다.
        results = self._run_paramiko_commands(COMMAND_ITEMS)

        # Step 5-a. 명령별 결과 중 실패 항목을 먼저 찾는다.
        failed = [item for item in results if item.get('rc') != 0]
        if failed:
            first = failed[0]
            display_command = first.get('display_command') or first.get('command')
            return self.fail(
                '점검 명령 실행 실패',
                message=f'{display_command} 명령 실행에 실패했습니다.',
                stdout=(first.get('stdout') or '').strip(),
                stderr=(first.get('stderr') or '').strip(),
            )

        if not results:
            return self.fail(
                '명령 실행 결과 없음',
                message='Paramiko 실행 결과가 비어 있습니다.',
            )

        # Step 5-b. 마지막 show 명령의 stdout을 꺼내서 metrics로 정리한다.
        last_result = results[-1]
        clock_output = (last_result.get('stdout') or '').strip()
        if not clock_output:
            return self.fail(
                '출력 파싱 실패',
                message='마지막 명령의 stdout이 비어 있습니다.',
                stdout='',
                stderr=(last_result.get('stderr') or '').strip(),
            )

        # Step 6. raw stdout 전체를 남기기보다 핵심 지표와 메시지를 우선 정리한다.
        return self.ok(
            metrics={
                'command_count': len(results),
                'last_command': last_result.get('display_command') or last_result.get('command'),
                'clock_output': clock_output,
            },
            thresholds={},
            reasons='Cisco IOS starter template이 Paramiko 명령 배열 실행과 결과 처리 흐름을 보여줍니다.',
            message=(
                'Cisco IOS starter 예시입니다. '
                f'last_command={last_result.get("display_command") or last_result.get("command")}'
            ),
        )


CHECK_CLASS = Check
