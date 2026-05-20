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
