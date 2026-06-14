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

HPUX-REPLAY-26

# is_required

권고

# inspection_name

NIC 이중화 점검

# inspection_content

HP-UX APA 또는 네트워크 이중화 구성의 정상 동작 여부를 점검한다.

# inspection_command

```bash
netstat -in
lanscan -q
```

# inspection_output

```text
Name  Mtu   Network         Address            Ipkts Ierrs Opkts Oerrs Coll
lan0  1500  192.168.1.0     192.168.1.136      12000     0 11000     0    0
lan1  1500  192.168.1.0     192.168.1.137      11800     0 10900     0    0

State of LAN Interface(s)
NamePPA  Hardware Path        Station Address    HP-DLPI   Link
lan0PPA  0/1/2/0/0/0           0x001560A1B2C3     UP        UP
lan1PPA  0/1/2/0/0/1           0x001560A1B2C4     UP        UP
```

# description

- `netstat -in`과 `lanscan -q`로 운영 NIC와 링크 상태, 오류 카운터를 확인한다.
- HP Auto Port Aggregation(APA) 구성 환경에서는 APA 관리 명령 또는 구성 파일로 active/standby 및 aggregation 상태를 추가 확인한다.
- 이중화 대상 NIC 중 하나라도 DOWN이면 단일 장애점 또는 failover 상태일 수 있다.
- 오류 카운터가 증가하거나 한쪽 링크만 동작하면 케이블, 스위치, APA 설정을 점검한다.

- **양호**: 이중화 대상 NIC가 모두 UP이고 오류 카운터 증가가 없는 경우
- **경고**: 이중화 대상 NIC DOWN, 오류 증가, active/standby 구성 불일치가 있는 경우
- **확인 필요**: APA 구성 여부 또는 기대 이중화 대상 NIC 목록이 불명확한 경우

# thresholds

[
    {id: null, key: "required_redundant_nic_count", value: "2", sortOrder: 0}
,
{id: null, key: "max_interface_error_count", value: "0", sortOrder: 1}
]

# inspection_script

# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


CHECK_COMMAND = 'nwmgr -S apa'
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

    def _parse_nwmgr(self, output: str, min_member_count: int = 2):     
        # VMS2:root[/]# nwmgr -S apa
        # Class    Mode        Load      Speed-               Membership
        # Instance             Balancing Duplex
        # ======== =========== ========= ==================== ===========================
        # lan900   LAN_MONITOR LB_HS     1.000000 Gbps Full Duplex2,4
        # lan901   LAN_MONITOR LB_HS     0.000000 Mbps        3*,5*
        # lan902   LAN_MONITOR LB_HS     10.000000 Gbps Full Duplex12,1
        # lan903   Not_Enabled LB_PORT   0.000000 Mbps         -
        # lan904   Not_Enabled LB_PORT   0.000000 Mbps         -
        results = []        
        for line in output.splitlines():
            line.strip()
            

            if not line.startswith("lan"):
                continue            
            if "LAN_MONITOR" not in line:
                continue

            member_match = re.search(r"(\d+\*?(?:,\d+\*?)*)\s*$", line)
            
            if not member_match:
                continue
            
            members_raw = member_match.group(1)

            members = [
                x.replace("*", "")
                for x in members_raw.split(",")
                if x.replace("*", "")
            ]

            agg_match = re.match("(lan\d+)", line)
            aggregate = agg_match.group(1)

            results.append({
                "aggregate": aggregate,
                "members": members,
                "member_count": len(members),
                "ok": len(members) >= min_member_count
            })

        return results 

    def run(self):
        try:
            metrics = {}

            min_member_count = self.get_threshold_var(key='MIN_MEMBER_COUNT', default=2, value_type='int')
            become_command = self._build_become_command()            
            check_commands = self._build_check_command(become_command)                        
            results = self._run_paramiko_commands(check_commands)            
            result = self._find_check_result(results)            
            output = result.get('stdout', '')            
           
            parsed = self._parse_nwmgr(output, min_member_count)
            metrics = parsed

            ok_items = [item for item in metrics if item.get("ok", False)]
            fail_items = [item for item in metrics if not item.get("ok", False)]

            is_pass = True if ok_items and not fail_items else False

            if is_pass:                
                return self.ok(
                    metrics = metrics,
                    reasons = f"NIC 이중화 상태가 정상 입니다. {ok_items}",
                    message = f"NIC 이중화 상태가 정상 입니다.",
                )
            else:
                return self.fail(
                    error="NIC 이중화 점검 실패",
                    metrics = metrics,   
                    message = f"NIC 이중화 상태 점검이 필요 합니다. {fail_items}",
                )
            
        except Exception as e:
            import traceback            
            return self.fail(
                error=f"NIC 이중화 점검 실패: {str(e)}",
                message=f"NIC 이중화 점검 실패: {str(e)}",                
            )

CHECK_CLASS = Check
