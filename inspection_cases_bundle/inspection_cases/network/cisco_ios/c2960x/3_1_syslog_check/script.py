# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


COMMAND = 'show logging'


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

    def _split_keywords(self, value):
        return [item for item in re.split(r'[\s,|]+', str(value or '')) if item]

    def run(self):
        keywords = self._split_keywords(self.get_threshold_var(
            'bad_log_keywords',
            default='critical,error,fail,down,flapping,overrun,stop',
            value_type='str',
        ))
        max_bad_count = self.get_threshold_var('max_bad_log_count', default=0, value_type='int')
        thresholds = {
            'bad_log_keywords': keywords,
            'max_bad_log_count': max_bad_count,
        }
        stdout, error = self._run_command()
        if error:
            return error
        if not stdout:
            return self.fail('시스템 로그 출력 없음', message='show logging 결과가 비어 있습니다.', thresholds=thresholds)

        pattern = re.compile('|'.join(re.escape(item) for item in keywords), re.IGNORECASE) if keywords else None
        bad_lines = []
        for line in stdout.splitlines():
            stripped = line.strip()
            if not stripped or stripped == COMMAND:
                continue
            if pattern and pattern.search(stripped):
                bad_lines.append(stripped)

        metrics = {
            'bad_log_count': len(bad_lines),
            'bad_logs': bad_lines,
        }
        if len(bad_lines) > max_bad_count:
            return self.warn(
                metrics=metrics,
                thresholds=thresholds,
                reasons='시스템 로그에서 장애 관련 키워드가 탐지되었습니다.',
                message=f'시스템 로그 경고: 장애 관련 로그 {len(bad_lines)}건.',
            )
        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='장애 관련 시스템 로그가 기준 이하입니다.',
            message='시스템 로그 점검 정상.',
        )


CHECK_CLASS = Check
