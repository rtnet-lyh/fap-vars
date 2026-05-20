# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


CHECK_COMMAND = 'bdf -i'
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

    def _parse_bdf(self, output: str, threshold: int):              
        pattern = re.compile(
            r"^/dev/\S+.*(?P<iuse>\d+)%\s+(?P<mount>/\S*)$",
            re.MULTILINE
        )
        results = []

        for match in pattern.finditer(output):
            iuse = int(match.group("iuse"))
            mount = match.group("mount")

            results.append({
                "mount": mount,
                "iused_percent": iuse,
                "ok": iuse <threshold
            })

        return results

    def run(self):
        try:
            metrics = {}

            max_usage = self.get_threshold_var(key='MAX_USAGE', default=80, value_type='int')

            become_command = self._build_become_command()            
            check_commands = self._build_check_command(become_command)                        
            results = self._run_paramiko_commands(check_commands)            
            result = self._find_check_result(results)            
            output = result.get('stdout', '')

            parsed = self._parse_bdf(output=output, threshold=max_usage)
            metrics = parsed
            fail_items = [item for item in parsed if not item["ok"]]

            avg_iused = round(
                sum(item["iused_percent"] for item in parsed) / len(parsed),
                2
            )
            metrics.append({"avg_iused": avg_iused})

            is_pass = True if not fail_items else False

            if is_pass:                
                return self.ok(
                    metrics = metrics,
                    reasons = f"iused 사용량이 정상입니다. 평균: {avg_iused}% / 임계치: {max_usage}%",
                    message = f"iused 사용량이 정상입니다. 평균: {avg_iused}% / 임계치: {max_usage}%",
                )
            else:
                return self.fail(
                    error="iused 사용량 점검 실패",
                    metrics = metrics,          
                    message = f"iused 사용량이 비정상입니다. 평균: {avg_iused}% / 임계치: {max_usage}%",
                )
            
        except Exception as e:    
            import traceback
            traceback.print_exc()
            return self.fail(
                error=f"iused 사용량 점검 실패: {str(e)}",
                message=f"iused 사용량 점검 실패: {str(e)}",                
            )

CHECK_CLASS = Check
