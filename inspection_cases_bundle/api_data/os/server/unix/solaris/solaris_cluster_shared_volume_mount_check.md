# type_name

일상점검

# area_name

server

# category_name

상태점검

# application_type

unix

# application

solaris

# inspection_code


SV-SOL-002

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
    {id: null, key: "sdfsdf", value: "sdfsf", sortOrder: 0}
]

# inspection_script

# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck

CHECK_COMMAND = 'mount'

class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'solaris'
    PARAMIKO_REUSE_SESSION = False
    
    def _parse_mount_lines(self, output, check_options, check_mounts):
        # mount
        # / on rpool/ROOT/solaris-1 read/write/setuid/devices/rstchown/dev=3e10002 on Thu Jan  1 09:00:00 1970
        # /var on rpool/ROOT/solaris-1/var read/write/setuid/devices/rstchown/nonbmand/exec/xattr/atime/dev=3e10003 on Wed Sep 24 20:25:42 2025
        # /devices on /devices read/write/setuid/devices/rstchown/dev=fff00000 on Wed Sep 24 20:25:42 2025
        # /dev on /dev read/write/setuid/devices/rstchown/dev=ffe40000 on Wed Sep 24 20:25:42 2025
        # /system/contract on ctfs read/write/setuid/devices/rstchown/dev=ffe00001 on Wed Sep 24 20:25:42 2025
        # /proc on proc read/write/setuid/devices/rstchown/dev=ffec0000 on Wed Sep 24 20:25:42 2025
        # /etc/mnttab on mnttab read/write/setuid/devices/rstchown/dev=ffdc0001 on Wed Sep 24 20:25:42 2025
        # /system/volatile on swap read/write/setuid/devices/rstchown/xattr/dev=ffd80001 on Wed Sep 24 20:25:42 2025
        # /tmp on swap read/write/setuid/devices/rstchown/xattr/dev=ffd80002 on Wed Sep 24 20:25:42 2025
        # /system/object on objfs read/write/setuid/devices/rstchown/dev=ffd40001 on Wed Sep 24 20:25:42 2025
        # /etc/dfs/sharetab on sharefs read/write/setuid/devices/rstchown/dev=ffd00001 on Wed Sep 24 20:25:42 2025
        # /dev/fd on fd read/write/setuid/devices/rstchown/dev=ffcc0001 on Wed Sep 24 20:25:42 2025
        # /var/share on rpool/VARSHARE read/write/nosetuid/devices/rstchown/nonbmand/noexec/noxattr/atime/dev=3e10006 on Wed Sep 24 20:25:56 2025
        # /var/tmp on rpool/VARSHARE/tmp read/write/setuid/devices/rstchown/nonbmand/exec/xattr/atime/dev=3e10007 on Wed Sep 24 20:25:56 2025
        # /var/share/kvol on rpool/VARSHARE/kvol read/write/nosetuid/devices/rstchown/nonbmand/noexec/noxattr/atime/dev=3e10008 on Wed Sep 24 20:25:57 2025
        # /media/Solaris-11_3_35_6_0-Boot-SPARC on /dev/dsk/c2t0d0s2 read only/nosetuid/nodevices/rstchown/noglobal/maplcase/rr/traildot/dev=2a8003a on Wed Sep 24 20:26:36 2025

        results = {}
        is_mount_cnt = 0
        is_check_cnt = 0
        
        for line in output.splitlines():            
            line = line.strip()
            if not line:
                continue
            
            match = re.search(r'^(\S+)\s+on\s+(\S+)\s+(.+?)\s+on', line)                        
            if not match:
                continue
            
            mount_point = match.group(1)
            device = match.group(2)
            options = match.group(3).split('/')

            is_mount = mount_point in check_mounts
            if is_mount:
                is_mount_cnt += 1

            is_check = all(opt in options for opt in check_options)
            if is_mount and is_check:
                is_check_cnt += 1

            results[mount_point] = {                
                "device": device,
                "options": options, 
                "exist_mount": is_mount,               
                "exist_option": is_check 
            }

        results["is_pass"] = True if (len(check_mounts) == is_mount_cnt and len(check_mounts) == is_check_cnt) else False

        return results 

    def run(self):
        check_mounts = self.get_threshold_var('check_mounts', default='/', value_type='str').strip()        
        check_options = self.get_threshold_var('check_options', default='read,write', value_type='str').strip()

        check_mounts = re.split(r'[,|]', check_mounts)
        check_options = re.split(r'[,|]', check_options)
    
        result = self._run_solaris_commands([
            {'command': CHECK_COMMAND, 'timeout': 5},
        ])[0]
       
        out = result['stdout']
        text = (out or '').strip()      

        parsed_rows = self._parse_mount_lines(output=text, check_options=check_options, check_mounts=check_mounts)    
        
        metrics = { 
            'is_pass': parsed_rows.get("is_pass", False),
            'mount_info': parsed_rows,
            'check_mounts': check_mounts,
            'check_options': check_options,            
        }

        thresholds = {
            'check_mounts': check_mounts,
            'check_options': check_options,                        
        }
          
        ok_items = []
        fail_items = []

        for mount_point in check_mounts:
            if parsed_rows.get(mount_point):
                if parsed_rows[mount_point]["exist_mount"] and parsed_rows[mount_point]["exist_option"]:
                    ok_items.append({
                        "mount_point": mount_point,
                        "options": parsed_rows[mount_point]["options"],
                        "device": parsed_rows[mount_point]["device"],
                        "check_options": check_options,
                    })
                else:
                    fail_items.append({
                        "mount_point": mount_point,
                        "options": parsed_rows[mount_point]["options"],
                        "device": parsed_rows[mount_point]["device"],
                        "check_options": check_options,
                    })
            else:
                fail_items.append({
                    "mount_point": mount_point,
                    "options": "unknown",
                    "device": "unknown",
                    "check_options": check_options,
                })
             
        if parsed_rows["is_pass"]:        
            return self.ok(
                metrics=metrics,
                thresholds=thresholds,
                reasons=(
                    f'공유 볼륨이 정상 마운트되어 있습니다. 성공정보: {ok_items}'                    
                ),
                message=(
                    f'공유 볼륨이 정상 마운트되어 있습니다. 성공정보: {ok_items}'                    
                ),
            )
        else:
            return self.fail(
                error='공유 볼륨 파일시스템 유형 이상',
                reasons=(
                    f'공유 볼륨 점검이 필요 합니다. {fail_items}'                    
                ),
                message=(
                    f'공유 볼륨 점검이 필요 합니다. {fail_items}'                                        
                ),
                metrics=metrics,
                thresholds=thresholds,
            )

CHECK_CLASS = Check
