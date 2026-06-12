# type_name

일상점검

# area_name

상태점검

# category_name

server

# application_type

unix

# application

hpux

# inspection_code

HPUX-REPLAY-04

# is_required

필수

# inspection_name

CPU 코어별 상태 점검

# inspection_content

물리 CPU 및 프로세서 인스턴스의 정상 인식 여부를 점검한다.

# inspection_command

```bash
ioscan -fnC processor
```

# inspection_output

```text
Class       I  H/W Path        Driver      S/W State   H/W Type     Description
===========================================================================
processor  0  120             processor   CLAIMED     PROCESSOR    Processor
processor  1  121             processor   CLAIMED     PROCESSOR    Processor
processor  2  122             processor   CLAIMED     PROCESSOR    Processor
processor  3  123             processor   CLAIMED     PROCESSOR    Processor
```

# description

- `ioscan -fnC processor` 명령으로 HP-UX가 인식한 CPU 프로세서 장치 상태를 확인한다.
- `S/W State`가 `CLAIMED`이면 OS가 해당 프로세서를 정상 인식한 상태로 본다.
- 프로세서가 `UNCLAIMED`, `NO_HW`, `ERROR` 등으로 표시되면 하드웨어 장애 또는 드라이버/펌웨어 문제 가능성이 있다.
- 기대 CPU 수와 실제 인식 수가 다르면 장비 구성, 파티션 설정, 장애 로그를 함께 확인한다.

- **양호**: 기대 CPU 수가 모두 확인되고 상태가 `CLAIMED`인 경우
- **경고**: CPU가 누락되었거나 `UNCLAIMED`, `NO_HW`, `ERROR` 상태가 있는 경우
- **확인 필요**: 기대 CPU 수 기준이 없거나 명령 실행 권한/환경 문제로 확인할 수 없는 경우

# thresholds

[
    {id: null, key: "expected_cpu_count", value: "0", sortOrder: 0}
,
{id: null, key: "allowed_processor_states", value: "CLAIMED", sortOrder: 1}
]

# inspection_script

# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck

CHECK_COMMAND = 'ioscan -fnC processor'
BECOME_COMMAND_TIMEOUT = 1

class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_AUTH_TIMEOUT_SEC = 30

    def _is_become_enabled(self):
        value = self.get_connection_value('become', default=False)
        return str(value).strip().lower() in ('1', 'true', 'y', 'yes', 'on')

    def _build_become_command(self):
        if not self._is_become_enabled():
            return ''

        method = str(self.get_connection_value('become_method', default='su -') or 'su -')
        method = ' '.join(method.strip().lower().split())
        user = str(self.get_connection_value('become_user', default='root') or 'root').strip() or 'root'

        if method == 'su':
            return 'su ' + user
        if method == 'su -':
            return 'su - ' + user
        if method == 'sudo':
            return 'sudo -u ' + user + ' -i'
        raise ValueError(f'unsupported become_method: {method}')

    def _build_check_command(self, become_command):

        if become_command:
            become_password = self.get_connection_value('become_password', default='')    
            return [
                {
                    'command': become_command,
                    'timeout': BECOME_COMMAND_TIMEOUT,
                    'ignore_prompt': True,                    
                },
                {
                    'command': become_password,
                    'hide_command': True,
                },
                {
                    'command': CHECK_COMMAND,
                }
            ]
        else:
            return [{'command': CHECK_COMMAND}]

    def _find_check_result(self, results):
        for item in reversed(results):
            if item.get('command') == CHECK_COMMAND:
                return item
        return None

    def _parse_ioscan_processor(self, output: str, ok_keyword: str):
        # VMS2:root[/]# ioscan -fnC processor
        # Class       I  H/W Path  Driver    S/W State   H/W Type     Description
        # ========================================================================
        # processor   0  0/120     processor   CLAIMED     PROCESSOR    Processor
        # processor   1  0/122     processor   CLAIMED     PROCESSOR    Processor
        # processor   2  0/124     processor   CLAIMED     PROCESSOR    Processor
        # processor   3  0/126     processor   CLAIMED     PROCESSOR    Processor
        # processor   4  0/128     processor   CLAIMED     PROCESSOR    Processor
        # processor   5  0/130     processor   CLAIMED     PROCESSOR    Processor
        # processor   6  0/132     processor   CLAIMED     PROCESSOR    Processor
        # processor   7  0/134     processor   CLAIMED     PROCESSOR    Processor
        # processor   8  0/136     processor   CLAIMED     PROCESSOR    Processor
        # processor   9  0/138     processor   CLAIMED     PROCESSOR    Processor
        # processor  10  0/140     processor   CLAIMED     PROCESSOR    Processor
        # processor  11  0/142     processor   CLAIMED     PROCESSOR    Processor
        # processor  12  0/144     processor   CLAIMED     PROCESSOR    Processor
        # processor  13  0/146     processor   CLAIMED     PROCESSOR    Processor
        # processor  14  0/148     processor   CLAIMED     PROCESSOR    Processor
        # processor  15  0/150     processor   CLAIMED     PROCESSOR    Processor
        pattern = re.compile(
            r"^processor\s+"
            r"(?P<index>\d+)\s+"
            r"(?P<hw_path>\S+)\s+"
            r"(?P<driver>\S+)\s+"
            r"(?P<sw_state>\S+)\s+"
            r"(?P<hw_type>\S+)\s+"
            r"(?P<description>.+)$"
        )
        
        ok_items = []
        fail_items = []

        for line in output.splitlines():
            line = line.strip()

            match = pattern.match(line)

            if not match:
                continue

            item = match.groupdict()

            if item["sw_state"].lower() == ok_keyword.lower():
                ok_items.append(item)
            else:
                fail_items.append(item)

        return ok_items, fail_items

    def run(self):
        try:

            become_command = self._build_become_command()
            commands = self._build_check_command(become_command)

            results = self._run_paramiko_commands(commands)
            result = self._find_check_result(results)

            metrics = {}

            ok_keyword = self.get_threshold_var(key='OK_KEYWORD', default='CLAIMED', value_type='str')

            if result is None:
                failed_result = next((item for item in results if item.get('rc') != 0), None)
                return self.fail(
                    error='명령 결과 없음',
                    message='명령 실행 결과를 찾지 못했습니다.',
                    stdout=(failed_result.get('stdout') or '').strip() if failed_result else '',
                    stderr=(failed_result.get('stderr') or '').strip() if failed_result else '',
                    metrics={
                        'executed_commands': [
                            item.get('display_command') or item.get('command')
                            for item in results
                        ],
                    },
                )

            output = result.get('stdout', '')            
            parsed = self._parse_ioscan_processor(output=output, ok_keyword=ok_keyword)                                  

            ok_items = parsed[0]
            fail_items = parsed[1]
            metrics = {
                "ok_items": ok_items,
                "fail_items": fail_items,
                "ok_keyword": ok_keyword
            }

            is_pass = True if not fail_items and ok_items else False

            if is_pass:    
                return self.ok(
                    metrics = metrics,
                    reasons = f"CPU 코어상태가 정상입니다.",
                    message = f"CPU 코어상태가 정상입니다. CPU 코어 개수: {len(ok_items)}, 상태: {ok_keyword}",
                    )
            else:
                return self.fail(
                    error="CPU 코어상태 점검 실패",
                    metrics = metrics,                
                    message=f"CPU 코어상태 점검이 필요합니다. 실패 CPU 정보: {fail_items}",
                )
            
        except Exception as e:
            import traceback            
            return self.fail(
                error=f"CPU 코어상태 점검 실패: {str(traceback.print_exc())}",
                message=f"CPU 코어상태 점검 실패: {str(traceback.print_exc())}",
            )

CHECK_CLASS = Check
