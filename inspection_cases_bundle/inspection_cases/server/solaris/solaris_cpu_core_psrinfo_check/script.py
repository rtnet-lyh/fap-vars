# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


PSRINFO_COMMAND = 'psrinfo'
ONLINE_KEYWORD = 'on-line'
OFFLINE_KEYWORD = 'off-line'
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
                    'command': PSRINFO_COMMAND,
                }
            ]
        else:
            return [{'command': PSRINFO_COMMAND}]
        
    def _find_check_result(self, results):
        for item in reversed(results):
            if item.get('command') == PSRINFO_COMMAND:
                return item
        return None
    
    def run(self):
        become_command = self._build_become_command()
        commands = self._build_check_command(become_command)

        results = self._run_paramiko_commands(commands)
        result = self._find_check_result(results)

        if result is None:
            failed_result = next((item for item in results if item.get('rc') != 0), None)
            return self.fail(
                error='psrinfo 명령 결과 없음',
                message='psrinfo 명령 실행 결과를 찾지 못했습니다.',
                stdout=(failed_result.get('stdout') or '').strip() if failed_result else '',
                stderr=(failed_result.get('stderr') or '').strip() if failed_result else '',
                metrics={
                    'executed_commands': [
                        item.get('display_command') or item.get('command')
                        for item in results
                    ],
                },
            )

        outputs = result.get('stdout', '')
        cpu_lines = outputs.splitlines()
        online_cpus = []
        offline_cpus = []

        for line in cpu_lines:
            if ONLINE_KEYWORD.lower() in line.lower():
                online_cpus.append(line)
            if OFFLINE_KEYWORD.lower() in line.lower():
                offline_cpus.append(line)
        
        metrics = {
            'online_cpus': online_cpus,
            'offline_cpus': offline_cpus
        }

        if offline_cpus:
            return self.fail(
                error = f'offline_cpu가 {len(offline_cpus)}개 존재합니다.',
                message = f'offline_cpu가 {len(offline_cpus)}개 존재합니다.',
                reasons = f'offline_cpu가 {len(offline_cpus)}개 존재합니다.',
                metrics = metrics
            )
        elif online_cpus:
            return self.ok(                
                message = f'offline_cpu가 존재하지 않습니다. online_cpu가 {len(online_cpus)}개 존재합니다.',
                reasons = f'offline_cpu가 존재하지 않습니다. online_cpu가 {len(online_cpus)}개 존재합니다.',
                metrics = metrics
            )        
        else:
            return self.fail(
                error = f'one/offline cpu 정보 수집에 실패하였습니다.',
                message = f'one/offline cpu 정보 수집에 실패하였습니다.',
                reasons = f'one/offline cpu 정보 수집에 실패하였습니다.',
                metrics = metrics
            )
        
CHECK_CLASS = Check
