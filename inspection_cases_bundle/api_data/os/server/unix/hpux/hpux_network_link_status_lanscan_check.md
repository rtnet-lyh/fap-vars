# type_name

일상점검

# area_name

server

# category_name

상태점검

# application_type

unix

# application

hpux

# inspection_code

HPUX-REPLAY-25

# is_required

필수

# inspection_name

NW 링크 상태 점검

# inspection_content

Network 연결상태 정상 유무 점검(NIC별 STATE Up, Down, Unknown 상태 확인)

# inspection_command

```bash
lanscan -q
lanadmin -x 0
```

# inspection_output

```text
State of LAN Interface(s)
NamePPA  Hardware Path        Station Address    HP-DLPI   Link
lan0PPA  0/1/2/0/0/0           0x001560A1B2C3     UP        UP
lan1PPA  0/1/2/0/0/1           0x001560A1B2C4     UP        DOWN

Interface = lan0
Link status   : Up
Speed         : 1000 Mbps
Duplex        : Full
Autoneg       : On
```

# description

- `lanscan -q` 명령으로 NIC별 링크 상태가 UP인지 확인한다.
- `lanadmin -x <ppa>` 명령으로 대상 NIC의 링크 상태, 속도, duplex 설정을 확인한다.
- 링크가 DOWN 또는 UNKNOWN이면 케이블, 스위치 포트, NIC 장애, 이중화 구성을 점검한다.
- 기대 속도가 정의된 경우 실제 속도와 duplex가 운영 기준과 일치해야 한다.

- **양호**: 운영 대상 NIC 링크가 UP이고 기대 속도 및 Full Duplex 기준을 만족하는 경우
- **경고**: 링크 DOWN/UNKNOWN, 속도 불일치, Half Duplex 상태가 확인되는 경우
- **확인 필요**: `lanadmin` 권한 문제 또는 PPA 매핑 확인이 불가능한 경우

# thresholds

[
    {id: null, key: "EXPECT_SPEED_MBPS", value: "1000", sortOrder: 0}
,
{id: null, key: "REQUIRE_FULL_DUPLEX", value: "true", sortOrder: 1}
]

# inspection_script

# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


CHECK_COMMAND = 'lanscan'
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
        become_password = self.get_connection_value('become_password', default='')                                        
        become_base_command = [
            {
                'command': become_command,
                'timeout': BECOME_COMMAND_TIMEOUT,
                'ignore_prompt': True,                    
            },
            {
                'command': become_password,
                'hide_command': True,
            }
        ]        
        if become_command:            
            become_base_command.append({"command": CHECK_COMMAND})
            return become_base_command
        else:
            return [{
                "command": CHECK_COMMAND
            }]   

    def _find_check_result(self, results):
        for item in reversed(results):
            if item.get('command') == CHECK_COMMAND:
                return item
        return None

    def _parse_lanscan(self, output: str, ok_word: str = 'UP'):     
        # VMS2:root[/]# lanscan
        # Hardware Station        Crd Hdw   Net-Interface  NM  MAC       HP-DLPI DLPI
        # Path     Address        In# State NamePPA        ID  Type      Support Mjr#
        # 0/0/0/7/0/0/1 0x1402EC74E211 3   UP    lan3 snap3     4   ETHER     Yes     119
        # 0/0/0/8/0/0/1 0x1402EC74E385 5   UP    lan5 snap5     6   ETHER     Yes     119
        # 0/0/0/28/0/0/0 0xD0BF9C40992A 6   UP    lan6 snap6     7   ETHER     Yes     119
        # 0/0/0/28/0/0/1 0xD0BF9C40992B 7   UP    lan7 snap7     8   ETHER     Yes     119
        # 0/0/0/28/2/0/0 0xD0BF9C40B998 8   UP    lan8 snap8     9   ETHER     Yes     119
        # 0/0/0/28/2/0/1 0xD0BF9C40B999 9   UP    lan9 snap9     10  ETHER     Yes     119
        # LinkAgg0 0x1402EC74E210 900 UP    lan900 snap900 12  ETHER     Yes     119
        # LinkAgg1 0x1402EC74E211 901 UP    lan901 snap901 13  ETHER     Yes     119
        # LinkAgg2 0x00237D6C7270 902 UP    lan902 snap902 14  ETHER     Yes     119
        # LinkAgg3 0x000000000000 903 DOWN  lan903 snap903 15  ETHER     Yes     119
        # LinkAgg4 0x000000000000 904 DOWN  lan904 snap904 16  ETHER     Yes     119

        pattern = re.compile(
            r"^(?P<hardware_path>\S+)\s+"
            r"(?P<station_address>\S+)\s+"
            r"(?P<interface_number>\d+)\s+"
            r"(?P<state>\S+)\s+"
            r"(?P<nameppa>\S+)\s+"
            r"(?P<snap>\S+)\s+",
            re.MULTILINE
        )

        results = []

        for match in pattern.finditer(output):            
            item = match.groupdict()

            if item["station_address"] != "0x000000000000":
                if item.get("state", "unknown") == ok_word:
                    item["ok"] = True
                else:
                    item["ok"] = False
                results.append(item)

        return results 

    def run(self):
        try:
            metrics = {}

            ok_word = self.get_threshold_var(key='OK_WORD', default='UP', value_type='str')
            become_command = self._build_become_command()            
            check_commands = self._build_check_command(become_command)                        
            results = self._run_paramiko_commands(check_commands)            
            result = self._find_check_result(results)            
            output = result.get('stdout', '')            
            
            parsed = self._parse_lanscan(output, ok_word)
            metrics = parsed

            ok_items = [item for item in metrics if item.get("ok", False)]
            fail_items = [item for item in metrics if not item.get("ok", False)]

            is_pass = True if ok_items and not fail_items else False

            if is_pass:                
                return self.ok(
                    metrics = metrics,
                    reasons = f"NIC 링크 상태가 정상 입니다. {ok_items}",
                    message = f"NIC 링크 상태가 정상 입니다.",
                )
            else:
                return self.fail(
                    error="NIC 링크 점검 실패",
                    metrics = metrics,   
                    message = f"NIC 링크 상태 점검이 필요 합니다. {fail_items}",
                )
            
        except Exception as e:
            import traceback            
            return self.fail(
                error=f"NIC 링크 상태 점검 실패: {str(e)}",
                message=f"NIC 링크 상태 점검 실패: {str(e)}",                
            )

CHECK_CLASS = Check
