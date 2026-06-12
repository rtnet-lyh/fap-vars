# -*- coding: utf-8 -*-

import re
import time
from collections import defaultdict

from .common._base import BaseCheck

CHECK_COMMAND = 'ioscan -m dsf'
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

    def _parse_ioscan_m_dsf(self, output: str):
        disks = defaultdict(list)
        current_disk = None

        for line in output.splitlines():
            line = line.strip()

            if not line:
                continue

            if line.startswith("="):
                continue
            
            if "Persistent DSF" in line or "Legacy DSF" in line:
                continue

            persistent_match = re.search(r"(/dev/rdisk/disk\d+)", line)
            legacy_paths = re.findall(r"(/dev/rdsk/\S+)", line)

            if persistent_match:
                current_disk = persistent_match.group(1)

                for path in legacy_paths:
                    disks[current_disk].append(path)

                continue

            if current_disk and legacy_paths:
                for path in legacy_paths:
                    disks[current_disk].append(path)
        
        return dict(disks)

    def _check_multipath(self, disks: dict, min_path_count=3):
        results = []
        
        for disk, paths in disks.items():            
            path_count = len(paths)

            if path_count == 1:
                continue

            if path_count >= min_path_count:
                status = True                
            else:
                status = False
            
            results.append({
                "disk": disk,
                "path_count": path_count,
                "status": status,
                "paths": paths,
            })

        return results 

    def _find_check_result(self, results):
        for item in reversed(results):
            if item.get('command') == CHECK_COMMAND:
                return item
        return None

    def run(self):
        try:

            become_command = self._build_become_command()
            commands = self._build_check_command(become_command)

            results = self._run_paramiko_commands(commands)
            result = self._find_check_result(results)

            metrics = {}

            min_path_count = self.get_threshold_var(key='MIN_PATH_COUNT', default=3, value_type='int')

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
            parsed = self._parse_ioscan_m_dsf(output=output)                      
            results = self._check_multipath(disks=parsed, min_path_count=min_path_count )                        

            if results:
                
                is_pass = all(item["status"] for item in results)                
                failed_items = [item for item in results if item["status"] is False]
                
                if is_pass:
                    return self.ok(
                        metrics = {"disk_count": len(results)},
                        reasons = f"모든 rdisk 디스크({len(results)})가 이중화 되어있습니다.",
                        message = f"모든 rdisk 디스크({len(results)})가 이중화 되어있습니다.",
                        )
                else:
                    return self.fail(
                        error="Path 이중화 점검 실패",
                        metrics = {"results": failed_items},                
                        message=f"Path 이중화 점검 실패: {failed_items}",                
                    )
            else:
                return self.fail(
                    error="Path 이중화 점검 실패",
                    message=f"Path 이중화 점검 실패: {results}",                
                )
        except Exception as e:
            import traceback

            return self.fail(
                error=f"Path 이중화 점검 실패: {str(traceback.print_exc())}",
                message=f"Path 이중화 점검 실패: {results}",                
            )

CHECK_CLASS = Check
