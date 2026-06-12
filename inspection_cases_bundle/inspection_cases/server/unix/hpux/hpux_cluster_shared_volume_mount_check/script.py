# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


CHECK_COMMAND = 'bdf'
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

    def _build_mount_points(self) ->list[str]:
        host_mount_points = self.get_host_var(key='mount_points', default=['/'])            
        threshold_mount_points = self.get_threshold_var(key='MOUNT_POINTS', default='/', value_type='str')
        threshold_mount_points = threshold_mount_points.strip().split("|")
        mount_points = host_mount_points + threshold_mount_points
        mount_points =list(set(mount_points))
            
        return mount_points

    def _find_check_result(self, results):
        for item in reversed(results):
            if item.get('command') == CHECK_COMMAND:
                return item
        return None

    def _parse_mount(self, output: str, target_mount_points):        
        fail_items = []        
        current_mount_point = re.findall(r"\s(/[\w/.-]*)\s*$", output, re.MULTILINE)

        for target in target_mount_points:
            if target not in current_mount_point:
                fail_items.append(target)

        return fail_items

    def run(self):
        try:
            metrics = {}
            target_mount_points = self._build_mount_points()

            become_command = self._build_become_command()            
            check_commands = self._build_check_command(become_command)                        
            results = self._run_paramiko_commands(check_commands)            
            result = self._find_check_result(results)            
            output = result.get('stdout', '')

            fail_items = self._parse_mount(output, target_mount_points)

            is_pass = True if not fail_items else False

            if is_pass:                
                return self.ok(
                    metrics = {
                        "target_mount_points": target_mount_points,
                        "missing_mount_points": fail_items
                    },
                    reasons = f"타겟 마운트가 정상적으로 조회 됩니다. 타겟 마운트: {target_mount_points}",
                    message = f"타겟 마운트가 정상적으로 조회 됩니다. 타겟 마운트: {target_mount_points}",
                )
            else:
                return self.fail(
                    error="타겟 마운트 점검 실패",
                    metrics = {
                        "target_mount_points": target_mount_points,
                        "missing_mount_points": fail_items
                    },           
                    message = f"일부 마운트가 조회되지 않습니다. {fail_items}",
                )
            
        except Exception as e:
            import traceback
            return self.fail(
                error=f"공유 볼룸상태 점검 실패: {str(e)}",
                message=f"공유 볼룸상태 점검 실패: {str(e)}",                
            )

CHECK_CLASS = Check
