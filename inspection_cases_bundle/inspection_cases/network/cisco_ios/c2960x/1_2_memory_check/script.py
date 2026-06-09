# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


COMMAND = 'show processes memory'
POOL_RE = re.compile(
    r'^\s*(?P<pool>.+?)\s+Pool Total:\s*(?P<total>\d+)\s+'
    r'Used:\s*(?P<used>\d+)\s+Free:\s*(?P<free>\d+)',
    re.IGNORECASE,
)


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'cisco_ios'
    PARAMIKO_REUSE_SESSION = True

    def _set_enable_password(self):
        data = self.get_connection_credential_data()
        for key in ('en_password', 'become_password'):
            value = self.get_connection_value(key, None)
            if value not in (None, ''):
                if isinstance(data, dict) and not data.get('en_password'):
                    data['en_password'] = str(value)
                return True
            value = self.get_application_credential_value(key, None)
            if value not in (None, ''):
                if isinstance(data, dict) and not data.get('en_password'):
                    data['en_password'] = str(value)
                return True
        return False

    def _run_command(self):
        commands = [
            {'command': 'terminal length 0'},
            {'command': COMMAND},
        ]
        results = self._run_paramiko_commands(commands, enable_mode=self._set_enable_password())
        failed = [item for item in results if item.get('rc') != 0]
        if failed:
            first = failed[0]
            command = first.get('display_command') or first.get('command')
            return None, self.fail(
                '점검 명령 실행 실패',
                message=f'{command} 명령 실행에 실패했습니다.',
                stdout=(first.get('stdout') or '').strip(),
                stderr=(first.get('stderr') or '').strip(),
            )
        return (results[-1].get('stdout') or '').strip(), None

    def _parse_pools(self, text):
        pools = []
        for line in (text or '').splitlines():
            match = POOL_RE.match(line)
            if not match:
                continue
            total = int(match.group('total'))
            used = int(match.group('used'))
            free = int(match.group('free'))
            pools.append({
                'pool': match.group('pool').strip(),
                'total_bytes': total,
                'used_bytes': used,
                'free_bytes': free,
                'usage_percent': round((used / total) * 100, 2) if total else 0.0,
            })
        return pools

    def run(self):
        max_usage = self.get_threshold_var(
            'max_memory_usage_percent',
            default=80.0,
            value_type='float',
        )
        thresholds = {'max_memory_usage_percent': max_usage}
        stdout, error = self._run_command()
        if error:
            return error

        pools = self._parse_pools(stdout)
        if not pools:
            return self.fail(
                '메모리 사용률 파싱 실패',
                message='show processes memory 출력에서 Pool 사용량을 찾지 못했습니다.',
                stdout=stdout,
                thresholds=thresholds,
            )

        max_pool = max(pools, key=lambda item: item['usage_percent'])
        over = [item for item in pools if item['usage_percent'] > max_usage]
        metrics = {
            'pool_count': len(pools),
            'max_memory_usage_percent': max_pool['usage_percent'],
            'max_memory_pool': max_pool['pool'],
            'over_threshold_pools': over,
            'pools': pools,
        }
        if over:
            return self.warn(
                metrics=metrics,
                thresholds=thresholds,
                reasons='메모리 사용률이 기준을 초과한 Pool이 있습니다.',
                message=f'메모리 사용률 경고: 최대 {max_pool["usage_percent"]}%, 기준 {max_usage}%.',
            )
        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='메모리 사용률이 기준 이하입니다.',
            message=f'메모리 사용률 점검 정상: 최대 {max_pool["usage_percent"]}%, 기준 {max_usage}%.',
        )


CHECK_CLASS = Check
