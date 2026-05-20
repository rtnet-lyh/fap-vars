# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck

CHECK_COMMAND = 'cmviewcl'
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

    def _parse_cmviewcl(self, output: str, bad_keywords: list[str]):
        # CLUSTER         STATUS
        # cluster_prod    up

        # NODE            STATUS          STATE
        # node1           up              running
        # node1           up              running

        # PACKAGE         STATUS          STATE
        # PKG_DB          up              running
        # PKG_WEB         up              running        
        bad_pattern = re.compile(
            rf"\b({bad_keywords})\b",
            re.IGNORECASE
        )        
        abnormal = []

        for line in output.splitlines():
            if bad_pattern.search(line):
                abnormal.append(line.strip())

        return abnormal

    def run(self):
        try:

            become_command = self._build_become_command()
            commands = self._build_check_command(become_command)

            results = self._run_paramiko_commands(commands)
            result = self._find_check_result(results)

            metrics = {}

            bad_keywords = self.get_threshold_var(
                key='BAD_KEYWORDS', 
                default='down|failed|halted|unknown|error|unavailable|not found', 
                value_type='str'
            ).lower()

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

            output = result.get('stdout', '').lower()   

            not_found_pattren = r"not found"

            if re.search(not_found_pattren, output, re.IGNORECASE):
                return self.ok(
                    metrics = metrics,
                    reasons = f"명령어({CHECK_COMMAND})가 존재하지 않습니다. 클러스터 데몬 미존재 서버로 판단하여 정상처리 하였습니다.",
                    message = f"명령어({CHECK_COMMAND})가 존재하지 않습니다. 클러스터 데몬 미존재 서버로 판단하여 정상처리 하였습니다.",
                )
                   
            parsed = self._parse_cmviewcl(output=output, bad_keywords=bad_keywords)                                  
            metrics = {
                "bad_keywords": bad_keywords,
                "bad_lines": parsed
            }

            is_pass = True if not parsed else False

            if is_pass:                                                
                return self.ok(
                    metrics = metrics,
                    reasons = f"Cluster 이중화 결과에 bad_keywords({bad_keywords})가 검출되지 않았습니다.",
                    message = f"Cluster 이중화 결과에 bad_keywords({bad_keywords})가 검출되지 않았습니다.",
                    )
            else:
                return self.fail(
                    error="Cluster 이중화 점검 실패",
                    metrics = metrics,                
                    message="Cluster 이중화 점검 실패. {parsed}",
                )
            
        except Exception as e:
            import traceback

            return self.fail(
                error=f"Cluster 이중화 점검 실패: {str(e)}",
                message=f"Cluster 이중화 점검 실패: {str(e)}",                
            )

CHECK_CLASS = Check
