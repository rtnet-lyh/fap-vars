# -*- coding: utf-8 -*-

import re
import time

from .common._base import BaseCheck

CHECK_COMMAND = 'ioscan -fnC disk'
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

    def _parse_hpux_disk_ioscan(self, output: str, ok_keyword: str):
        # VMS2:root[/]# ioscan -fnC disk
        # Class     I  H/W Path        Driver S/W State   H/W Type     Description
        # ========================================================================
        # disk      0  0/0/0/1/0/0/0.0.0              sdisk   CLAIMED     DEVICE       HP      LOGICAL VOLUME
        #                             /dev/dsk/c0t0d0     /dev/dsk/c0t0d0s2   /dev/rdsk/c0t0d0    /dev/rdsk/c0t0d0s2
        #                             /dev/dsk/c0t0d0s1   /dev/dsk/c0t0d0s3   /dev/rdsk/c0t0d0s1  /dev/rdsk/c0t0d0s3
        # disk      1  0/0/0/1/0/0/0.0.1              sdisk   CLAIMED     DEVICE       HP      LOGICAL VOLUME
        #                             /dev/dsk/c0t0d1   /dev/rdsk/c0t0d1
        # disk    3085  0/0/0/1/0/0/0.0.2              sdisk   CLAIMED     DEVICE       HP      LOGICAL VOLUME
        #                             /dev/dsk/c0t0d2     /dev/dsk/c0t0d2s2   /dev/rdsk/c0t0d2    /dev/rdsk/c0t0d2s2
        #                             /dev/dsk/c0t0d2s1   /dev/dsk/c0t0d2s3   /dev/rdsk/c0t0d2s1  /dev/rdsk/c0t0d2s3
        # disk    662  0/0/0/9/0/0/0.207.31.0.0.0.1   sdisk   CLAIMED     DEVICE       3PARdataVV
        #                             /dev/dsk/c34t0d1   /dev/rdsk/c34t0d1
        # disk    663  0/0/0/9/0/0/0.207.31.0.0.0.2   sdisk   CLAIMED     DEVICE       3PARdataVV
        #                             /dev/dsk/c34t0d2   /dev/rdsk/c34t0d2
        # disk    664  0/0/0/9/0/0/0.207.31.0.0.0.3   sdisk   CLAIMED     DEVICE       3PARdataVV
        #                             /dev/dsk/c34t0d3   /dev/rdsk/c34t0d3
        # disk    665  0/0/0/9/0/0/0.207.31.0.0.0.4   sdisk   CLAIMED     DEVICE       3PARdataVV
        #                             /dev/dsk/c34t0d4   /dev/rdsk/c34t0d4
        # disk    666  0/0/0/9/0/0/0.207.31.0.0.0.5   sdisk   CLAIMED     DEVICE       3PARdataVV
        #                             /dev/dsk/c34t0d5   /dev/rdsk/c34t0d5
        # disk    667  0/0/0/9/0/0/0.207.31.0.0.0.6   sdisk   CLAIMED     DEVICE       3PARdataVV
        #                             /dev/dsk/c34t0d6   /dev/rdsk/c34t0d6

        pattern = re.compile(
            r"^disk\s+"            
            r"(?P<instance>\d+)\s+"
            r"(?P<hw_path>\S+)\s+"
            r"(?P<driver>\S+)\s+"
            r"(?P<state>\S+)\s+"
            r"(?P<hw_type>\S+)\s+",
            re.MULTILINE
        )

        results = []

        for match in pattern.finditer(output):
            item = match.groupdict()

            item["ok"] = item["state"] == ok_keyword

            results.append(item)

        return results

    def run(self):
        try:

            become_command = self._build_become_command()
            commands = self._build_check_command(become_command)

            results = self._run_paramiko_commands(commands)
            result = self._find_check_result(results)

            metrics = {}

            ok_keyword = self.get_threshold_var(key='OK_KEYWORD', default='CLAIMED', value_type='float')

            output = result.get('stdout', '')            
            parsed = self._parse_hpux_disk_ioscan(
                output=output,
                ok_keyword=ok_keyword,                
            )

            ok_items = [item for item in parsed if item.get("ok", False)]
            fail_items = [item for item in parsed if not item.get("ok", False)]

            is_pass = True if ok_items and not fail_items else False

            metrics["disk_count"] = len(parsed)
            metrics["ok_count"] = len(ok_items)
            metrics["fail_count"] = len(fail_items)
            metrics["fail_items"] = fail_items
            metrics["is_pass"] = is_pass
                
            if is_pass:
                return self.ok(
                    metrics = metrics,
                    reasons = f"DISK 인식 상태가 정상입니다. {metrics}",
                    message = f"DISK 인식 상태가 정상입니다. {metrics}",
                )
            else:
                return self.fail(
                    error="DISK 인식 상태 불량",                        
                    metrics = metrics,
                    reasons = f"DISK 인식 상태 점검이 필요 합니다. {metrics}",
                    message = f"DISK 인식 상태 점검이 필요 합니다. {metrics}",
                )

        except Exception as e:
            return self.fail(
                error=f"DISK 인식 상태 점검 실패: {str(e)}",
                message=f"DISK 인식 상태 점검 실패: {str(e)}",                
            )

CHECK_CLASS = Check