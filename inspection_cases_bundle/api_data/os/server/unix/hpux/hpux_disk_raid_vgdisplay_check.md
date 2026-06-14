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

HPUX-REPLAY-08

# is_required

권고

# inspection_name

Disk 이중화 정상 여부

# inspection_content

볼륨 그룹과 물리 볼륨 상태를 통해 디스크 이중화 정상 여부를 점검한다.

# inspection_command

```bash
vgdisplay -v
```

# inspection_output

```text
--- Volume groups ---
VG Name                     /dev/vg00
VG Status                   available
Max PV                      16
Cur PV                      2
Act PV                      2

--- Physical volumes ---
PV Name                     /dev/dsk/c0t0d0
PV Status                   available
PV Name                     /dev/dsk/c1t0d0
PV Status                   available
```

# description

- `vgdisplay -v` 명령으로 HP-UX LVM 볼륨 그룹과 물리 볼륨 상태를 확인한다.
- 운영 디스크가 LVM 미러링 또는 스토리지 이중화 구조로 구성되어 있는지 확인한다.
- `Cur PV`와 `Act PV`가 다르거나 `PV Status`가 `available`이 아니면 디스크 경로 또는 물리 디스크 이상 가능성이 있다.
- 하드웨어 RAID 또는 외장 스토리지 이중화 환경은 별도 관리 도구 결과와 함께 표기한다.

- **양호**: 필요한 물리 볼륨이 모두 `available`이고 활성 PV 수가 기대값과 일치하는 경우
- **경고**: PV 누락, 비활성 PV, 미러 장애, 활성 PV 수 불일치가 있는 경우
- **확인 필요**: 하드웨어 RAID 등 OS 명령만으로 이중화 상태 판단이 어려운 경우

# thresholds

[
    {id: null, key: "expected_active_pv_count", value: "0", sortOrder: 0}
,
{id: null, key: "required_pv_status", value: "available", sortOrder: 1}
]

# inspection_script

# -*- coding: utf-8 -*-

import re
import time 

from .common._base import BaseCheck


CHECK_COMMAND = 'scsimgr lun_map | egrep "LUN|PATH COUNT|ACTIVE PATH"'
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

    def _parse_scsimgr(self, output: str, min_multipath_count=1):   
        # LUN PATH INFORMATION FOR LUN : /dev/rdisk/disk3082
        # Total number of LUN paths     = 3
        # LUN path : lunpath1509
        # LUN path : lunpath1320
        # LUN path : lunpath2406
        #         LUN PATH INFORMATION FOR LUN : /dev/rdisk/disk3083
        # Total number of LUN paths     = 2
        # LUN path : lunpath1590
        # LUN path : lunpath1318
        #         LUN PATH INFORMATION FOR LUN : /dev/rdisk/disk3086
        # Total number of LUN paths     = 1
        # LUN path : lunpath2675     
        lun_blocks = re.findall(
            r"LUN PATH INFORMATION FOR LUN\s*:\s*(.+?)(?=LUN PATH INFORMATION FOR LUN|\Z)",
            output,
            re.S
        )
        ok_items = []
        failed_items = []

        for block in lun_blocks:
            disk_match = re.search(r"(/dev/rdisk/\S+)", block)            
            path_count_match = re.search(r"Total number of LUN paths\s*=\s*(\d+)", block)            
            paths = re.findall(r"LUN path\s*:\s*(\S+)", block)

            if disk_match and path_count_match:
                disk = disk_match.group(1)
                path_count = int(path_count_match.group(1))            
                multipath_ok = path_count >= min_multipath_count

                if multipath_ok:
                    ok_items.append({
                        "disk": disk,
                        "path_count": path_count,
                        "paths": paths
                    })
                else:
                    failed_items.append({
                        "disk": disk,
                        "path_count": path_count,
                        "paths": paths
                    })
            
        return ok_items, failed_items
            
    def run(self):
        try:
            metrics = {}

            min_multipath_count = self.get_threshold_var(key='MIN_MULTIPATH_COUNT', default=2, value_type='int')

            become_command = self._build_become_command()            
            check_commands = self._build_check_command(become_command)                        
            results = self._run_paramiko_commands(check_commands)            
            result = self._find_check_result(results)            
            output = result.get('stdout', '')


            ok_items, failed_items = self._parse_scsimgr(output=output, min_multipath_count=min_multipath_count)
            
            is_pass = True if (ok_items and not failed_items) else False

            metrics = {
                "total_disk_count": len(ok_items) + len(failed_items),                
                "min_multipath_count": min_multipath_count,
                "failed_items": failed_items
            }

            if is_pass:                
                return self.ok(
                    metrics = metrics,
                    reasons = f"디스크 이중화 상태가 정상 입니다. 최소 LUN path: {min_multipath_count}",
                    message = f"디스크 이중화 상태가 정상 입니다. 최소 LUN path: {min_multipath_count}",
                )
            else:
                return self.warn(                    
                    metrics = metrics,         
                    reasons = f"디스크 중에 LUN path의 개수가 {min_multipath_count} 보다 적은 디스크가 존재 합니다.",
                    message = f"디스크 중에 LUN path의 개수가 {min_multipath_count} 보다 적은 디스크가 존재 합니다."
                )
            
        except Exception as e:
            import traceback
            return self.fail(
                error=f"공유 볼룸상태 점검 실패: {str(e)}",
                message=f"공유 볼룸상태 점검 실패: {str(e)}",                
            )

CHECK_CLASS = Check
