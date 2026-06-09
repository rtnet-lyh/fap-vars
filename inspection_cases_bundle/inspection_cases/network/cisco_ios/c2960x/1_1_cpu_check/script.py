# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


COMMAND = 'show processes cpu'
CPU_RE = re.compile(
    r'CPU utilization for five seconds:\s*([0-9.]+)%'
    r'(?:/[0-9.]+%)?;\s*one minute:\s*([0-9.]+)%;\s*'
    r'five minutes:\s*([0-9.]+)%',
    re.IGNORECASE,
)
PROCESS_RE = re.compile(
    r'^\s*(\d+)\s+\d+\s+\d+\s+\d+\s+'
    r'([0-9.]+)%\s+([0-9.]+)%\s+([0-9.]+)%\s+\S+\s+(.+?)\s*$'
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

    def _top_processes(self, text):
        rows = []
        for line in (text or '').splitlines():
            match = PROCESS_RE.match(line)
            if not match:
                continue
            rows.append({
                'pid': int(match.group(1)),
                'cpu_5sec_percent': round(float(match.group(2)), 2),
                'cpu_1min_percent': round(float(match.group(3)), 2),
                'cpu_5min_percent': round(float(match.group(4)), 2),
                'process': match.group(5).strip(),
            })
            if len(rows) >= 5:
                break
        return rows

    def run(self):
        max_usage = self.get_threshold_var(
            'max_cpu_usage_percent',
            default=80.0,
            value_type='float',
        )
        thresholds = {'max_cpu_usage_percent': max_usage}
        stdout, error = self._run_command()
        if error:
            return error

        match = CPU_RE.search(stdout)
        if not match:
            return self.fail(
                'CPU 사용률 파싱 실패',
                message='show processes cpu 출력에서 CPU 사용률을 찾지 못했습니다.',
                stdout=stdout,
                thresholds=thresholds,
            )

        usage_5sec, usage_1min, usage_5min = [round(float(value), 2) for value in match.groups()]
        metrics = {
            'cpu_usage_5sec_percent': usage_5sec,
            'cpu_usage_1min_percent': usage_1min,
            'cpu_usage_5min_percent': usage_5min,
            'top_processes': self._top_processes(stdout),
        }
        if usage_5min > max_usage:
            return self.fail(
                'CPU 사용률 임계치 초과',
                message=f'5분 평균 CPU 사용률 {usage_5min}%가 기준 {max_usage}%를 초과했습니다.',
                stdout=stdout,
                metrics=metrics,
                thresholds=thresholds,
            )
        if usage_5sec > max_usage or usage_1min > max_usage:
            return self.warn(
                metrics=metrics,
                thresholds=thresholds,
                reasons='단기 CPU 사용률이 기준을 초과했습니다.',
                message=f'CPU 사용률 단기 경고: 5초={usage_5sec}%, 1분={usage_1min}%, 기준={max_usage}%.',
            )
        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='CPU 사용률이 기준 이하입니다.',
            message=f'CPU 사용률 점검 정상: 5분 평균 {usage_5min}%, 기준 {max_usage}%.',
        )


CHECK_CLASS = Check
