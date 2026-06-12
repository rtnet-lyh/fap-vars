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
