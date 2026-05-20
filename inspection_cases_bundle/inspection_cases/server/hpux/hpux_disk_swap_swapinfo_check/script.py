# -*- coding: utf-8 -*-

import re
import time

from .common._base import BaseCheck

CHECK_COMMAND = 'swapinfo -a'
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

    def _parse_hpux_swapinfo(self, output: str, max_pct_usage: float):
        # VMS2:root[/]#  swapinfo -a
        #                 Kb          Kb           Kb   PCT      START/          Kb
        # TYPE          AVAIL        USED         FREE  USED       LIMIT     RESERVE  PRI  NAME
        # dev        50331648           0     50331648    0%           0           -    1  /dev/vg00/lvol2
        # reserve           -     1629464     -1629464
        # memory     31793264     6713212     25080052   21%

        pattern = re.compile(            
            r"^(?P<type>\S+)\s+"
            r"(?P<avail>\S+)\s+"
            r"(?P<used>-?\d+)\s+"
            r"(?P<free>-?\d+)"
            r"(?:\s+(?P<pct>\d+)%)?",
            re.MULTILINE
        )

        results = []

        for match in pattern.finditer(output):            
            item = match.groupdict()
            
            used = int(item["used"])

            if used > 0:
                pct = int(item.get("pct") or 0)

                item["used"] = used
                item["pct"] = pct

                item["ok"] = pct < max_pct_usage

                results.append(item)

        return results

    def run(self):
        try:
            become_command = self._build_become_command()
            commands = self._build_check_command(become_command)

            results = self._run_paramiko_commands(commands)
            result = self._find_check_result(results)

            metrics = {}

            max_pct_usage = self.get_threshold_var(key='MAX_PCT_USAGE', default=80, value_type='float')

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
            parsed = self._parse_hpux_swapinfo(
                output=output,
                max_pct_usage=max_pct_usage
            )
                
            metrics = parsed 

            ok_items = [item for item in metrics if item.get("ok", False)]
            fail_items = [item for item in metrics if not item.get("ok", False)]

            is_pass = True if ok_items and not fail_items else False
                
            if is_pass:
                return self.ok(
                    metrics = metrics,
                    reasons = f"DISK Swap 상태가 정상입니다. {ok_items}",
                    message = f"DISK Swap 상태가 정상입니다. {ok_items}",
                )
            else:
                return self.fail(
                    error="DISK I/O 임계치 초과",                        
                    metrics = metrics,
                    reasons = f"DISK Swap 상태 점검이 필요 합니다. {fail_items}",
                    message = f"DISK Swap 상태 점검이 필요 합니다. {fail_items}",
                )

        except Exception as e:
            return self.fail(
                error=f"DISK Swap 점검 실패: {str(e)}",
                message=f"DISK Swap 점검 실패: {str(e)}",                
            )

CHECK_CLASS = Check