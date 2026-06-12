# type_name

일상점검

# area_name

상태점검

# category_name

server

# application_type

unix

# application

solaris

# inspection_code

SOL-REPLAY-NET-03

# is_required

# inspection_name

# inspection_content

# inspection_command

```bash

```

# inspection_output

```text

```

# description

# thresholds

[
    {id: null, key: "max_packet_loss_percent", value: "0", sortOrder: 0}
,
{id: null, key: "max_avg_rtt_ms", value: "100", sortOrder: 1}
,
{id: null, key: "failure_keywords", value: "", sortOrder: 2}
]

# inspection_script

# -*- coding: utf-8 -*-

import re
from .common._base import BaseCheck

class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'solaris'
    PARAMIKO_REUSE_SESSION = False

    def _check_ping_result(self, output:str, ok_keyword: str):
        return True if re.search(ok_keyword, output) else False

    def run(self):
        ok_keyword = self.get_threshold_var('ok_keyword', default='is alive', value_type='str')
        target_ip = self.get_threshold_var('target_ip', default='', value_type='str')

        if not target_ip:
            result = self._run_solaris_commands([
                {'command': "netstat -rn | awk '/^default/ {print $2}'", 'timeout': 5},
            ], become_required=True)[0]
            
            target_ip = result['stdout']        

        result = self._run_solaris_commands([
            {'command': f"ping {target_ip} 3", 'timeout': 5},
        ], become_required=True)[0]

        out = result['stdout']        
        text = (out or '').strip()
        
        is_pass = self._check_ping_result(text, ok_keyword)

        metrics = {
            'ping_output': text,
            'is_pass': is_pass,
            'ok_keyword': ok_keyword,
            'target_ip': target_ip,            
        }

        thresholds = {
            'ok_keyword': ok_keyword,
            'target_ip': target_ip,
        }

        if is_pass:
            return self.ok(
                metrics=metrics,
                thresholds=thresholds,
                reasons=f"ping 점검이 정상입니다. target_ip: {target_ip}, ping_output: {text}",
                message=f"ping 점검이 정상입니다. target_ip: {target_ip}, ping_output: {text}",
            )

        else:
            return self.fail(
                error='ping 점검실패',
                metrics=metrics,
                thresholds=thresholds,
                reasons=f"ping 점검 실패. target_ip: {target_ip}, ping_output: {text}",
                message=f"ping 점검 실패. target_ip: {target_ip}, ping_output: {text}",
            )

CHECK_CLASS = Check
