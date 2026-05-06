# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


CHECK_COMMAND = "printf '\\n' | format"
BECOME_COMMAND_TIMEOUT = 1

class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_AUTH_TIMEOUT_SEC = 30

    def _build_become_command(self):
        become = self.get_connection_value('become', default=False)
        become_method = self.get_connection_value('become_method', default='su -')
        become_user = self.get_connection_value('become_user', default='root')        

        if become_method not in ['su', 'su -', 'sudo']:
            ValueError(f'unsupported become_method: {become_method}')
        
        if become:
            return f'{become_method} {become_user}'
                
        return ''

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
    
    def _split_keywords(self, raw_value):
        return [token.strip() for token in str(raw_value or '').split(',') if token.strip()]

    def _parse_disk_names(self, output):
        disks = []
        for line in str(output or '').splitlines():
            match = re.match(r'^\s*\d+\.\s+(\S+)', line)
            if match:
                disks.append(match.group(1))
        return disks

    def run(self):
        min_disk_count = self.get_threshold_var('expected_disk_count', default=1, value_type=int)
        failure_keywords = self._split_keywords(
            self.get_threshold_var(
                'failure_keywords',
                default='Unknown,Drive not available',
                value_type=str,
            )
        )
        become_command = self._build_become_command()
        commands = self._build_check_command(become_command)

        results = self._run_paramiko_commands(commands)
        result = self._find_check_result(results)

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

        if result.get('rc') != 0:
            return self.fail(
                error='format 명령 실행 실패',
                message='Solaris format 명령 실행에 실패했습니다.',
                stdout=(result.get('stdout') or '').strip(),
                stderr=(result.get('stderr') or '').strip(),
            )

        output = result.get('stdout', '')
        disk_names = self._parse_disk_names(output)
        disk_count = len(disk_names)
        matched_failure_keywords = [
            keyword for keyword in failure_keywords
            if keyword.lower() in output.lower()
        ]
        
        metrics = {            
            'disk_count': disk_count,
            'disk_names': disk_names,
            'matched_failure_keywords': matched_failure_keywords,
        }

        if matched_failure_keywords:
            return self.fail(
                error='Disk 인식 실패 키워드 감지',
                message=f'Disk 인식 출력에서 실패 키워드가 확인되었습니다: {", ".join(matched_failure_keywords)}',
                reasons=f'Disk 인식 출력에서 실패 키워드가 확인되었습니다: {", ".join(matched_failure_keywords)}',
                metrics=metrics,
            )

        if disk_count >= min_disk_count:
            return self.ok(
                message=f'Disk 인식 개수가 정상({disk_count})입니다. 최소개수는 {min_disk_count}입니다.',
                reasons=f'format 출력에서 디스크 {disk_count}개가 확인되었습니다.',
                metrics=metrics,
                thresholds={
                    'expected_disk_count': min_disk_count,
                    'failure_keywords': failure_keywords,
                },
            )

        return self.fail(
            error=f'Disk 인식 개수가 비정상({disk_count})입니다. 최소개수는 {min_disk_count}입니다.',
            message=f'Disk 인식 개수가 비정상({disk_count})입니다. 최소개수는 {min_disk_count}입니다.',
            reasons=f'format 출력에서 기준보다 적은 디스크 {disk_count}개만 확인되었습니다.',
            metrics=metrics,
            thresholds={
                'expected_disk_count': min_disk_count,
                'failure_keywords': failure_keywords,
            },
        )
        
CHECK_CLASS = Check
