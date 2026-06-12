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

SOL-REPLAY-MEM-02

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
    {id: null, key: "expected_memory_mb", value: "8192", sortOrder: 0}
,
{id: null, key: "min_dimm_count", value: "1", sortOrder: 1}
,
{id: null, key: "failure_keywords", value: "장치를 찾을 수 없습니다,not found,cannot,command not found,module missing", sortOrder: 2}
]

# inspection_script

# -*- coding: utf-8 -*-

import re
from .common._base import BaseCheck


PRTDIAG_COMMAND = 'prtconf | grep Memory'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'solaris'
    PARAMIKO_REUSE_SESSION = False

    def _parse_memory_size(self, text, min_memory_mb):
        match = re.search(r'Memory size:\s+(\d+)\s+(\S+)', text)
        
        if match:
            memory_size = int(match.group(1))
            return {
                "memory_size": memory_size,
                "unit": match.group(2),
                "is_ok": memory_size >= min_memory_mb
            }
        else:
            return {
                "memory_size": "unknown",
                "unit": "unknown",
                "is_ok": False,
            }


    def run(self):
        min_memory_mb = self.get_threshold_var('min_memory_mb', default=16000, value_type='int')

        result = self._run_solaris_commands([
            {'command': PRTDIAG_COMMAND, 'timeout': 5},
        ], become_required=True)[0]
        
        out = result['stdout']        
        text = (out or '').strip()

        parsed_memory = self._parse_memory_size(text, min_memory_mb)        
        
        metrics = {
            'min_memory_mb': min_memory_mb,
            'memory_info': parsed_memory,            
        }

        thresholds = {
            'min_memory_mb': min_memory_mb,
        }

        if parsed_memory.get("is_ok"):
            return self.ok(
                metrics=metrics,
                thresholds=thresholds,
                reasons=f'메모리 상태 점검에 성공했습니다. {parsed_memory}',                 
                message=f'메모리 상태 점검에 성공했습니다. {parsed_memory}',                 
            )
        else:
            return self.fail(
                error='Memory 점검 필요', 
                message=f'메모리 상태 점검에 실패했습니다. {parsed_memory}',                 
            )



CHECK_CLASS = Check
