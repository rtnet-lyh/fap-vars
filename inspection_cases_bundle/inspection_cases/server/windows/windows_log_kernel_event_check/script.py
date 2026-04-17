# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


LOG_KERNAL_COMMAND = (
    "$e=Get-WinEvent -FilterHashtable @{LogName=@('System','Application'); StartTime=(Get-Date).AddDays(-30)} -ErrorAction SilentlyContinue | "
    "Where-Object { $_.ProviderName -match 'BugCheck|Microsoft-Windows-WER-SystemErrorReporting|Microsoft-Windows-Kernel-Power' -or $_.Message -match '(?i)bugcheck|bluescreen|livekernelevent|kernel panic|panicking' -or ($_.Id -eq 41 -and $_.ProviderName -eq 'Microsoft-Windows-Kernel-Power') } | "
    "Select-Object TimeCreated,LogName,ProviderName,Id,LevelDisplayName,@{N='Message';E={($_.Message -replace '\\r?\\n',' ')}}; "
    "if($e){$e | Format-Table -Wrap -Auto}else{'No panic-like kernel events found in the last 30 days.'}"
)


def _parse_int(value):
    return int(str(value).strip())


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'winrm'
    WINRM_SHELL = 'powershell'

    def run(self):
        max_panic_like_event_count = self.get_threshold_var('max_panic_like_event_count', default=0, value_type='int')
        failure_keywords_raw = self.get_threshold_var('failure_keywords', default='', value_type='str')

        rc, out, err = self._run_ps(LOG_KERNAL_COMMAND)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'WinRM 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if self._is_not_applicable(rc, err):
            return self.not_applicable(
                'WinRM 실행 환경을 사용할 수 없습니다.',
                raw_output=(err or '').strip(),
            )

        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='Windows 커널 로그 점검 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        text = (out or '').strip()
        if not text:
            return self.ok(
                metrics={
                    'panic_like_event_count': 0,
                    'bugcheck_event_count': 0,
                    'kernel_power_41_count': 0,
                    'live_kernel_event_count': 0,
                    'matched_failure_keywords': [],
                },
                thresholds={
                    'max_panic_like_event_count': max_panic_like_event_count,
                    'failure_keywords': [],
                },
                reasons='최근 30일 내 커널 패닉 유사 이벤트가 확인되지 않았습니다.',
                message='Windows 커널 로그 점검이 정상 수행되었습니다.',
            )

        if 'No panic-like kernel events found in the last 30 days.' in text:
            return self.ok(
                metrics={
                    'panic_like_event_count': 0,
                    'bugcheck_event_count': 0,
                    'kernel_power_41_count': 0,
                    'live_kernel_event_count': 0,
                    'matched_failure_keywords': [],
                },
                thresholds={
                    'max_panic_like_event_count': max_panic_like_event_count,
                    'failure_keywords': [],
                },
                reasons='최근 30일 내 커널 패닉 유사 이벤트가 확인되지 않았습니다.',
                message='Windows 커널 로그 점검이 정상 수행되었습니다.',
            )

        failure_keywords = [
            keyword.strip()
            for keyword in failure_keywords_raw.split(',')
            if keyword.strip()
        ]
        matched_failure_keywords = [
            keyword for keyword in failure_keywords if keyword.lower() in text.lower()
        ]
        if matched_failure_keywords:
            return self.fail(
                '커널 로그 실패 키워드 감지',
                message='커널 로그 결과에서 실패 키워드가 확인되었습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        lines = [line.rstrip() for line in text.splitlines() if line.strip()]
        if len(lines) < 1:
            return self.fail(
                '커널 로그 정보 없음',
                message='커널 로그 결과를 해석할 수 없습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        entries = []
        entry_pattern = re.compile(
            r'^(?P<time>\d{4}-\d{2}-\d{2}\s+(?:오전|오후)\s+\d{1,2}:\d{2}:\d{2})\s+'
            r'(?P<logname>\S+)\s+'
            r'(?P<provider>.+?)\s+'
            r'(?P<id>\d+)\s+'
            r'(?P<level>오류|경고|정보|Error|Warning|Critical|Information)\s+'
            r'(?P<message>.+)$'
        )
        for line in lines:
            if line.lstrip().startswith('---') or line.startswith('TimeCreated') or line.startswith('-----------'):
                continue
            match = entry_pattern.match(line)
            if not match:
                continue
            entries.append({
                'time_created': match.group('time'),
                'log_name': match.group('logname'),
                'provider_name': match.group('provider').strip(),
                'event_id': _parse_int(match.group('id')),
                'level': match.group('level').strip(),
                'message': match.group('message').strip(),
            })

        if not entries:
            return self.fail(
                '커널 로그 파싱 실패',
                message='커널 패닉 유사 이벤트 항목을 해석하지 못했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        bugcheck_entries = [
            entry for entry in entries
            if 'bugcheck' in entry['provider_name'].lower() or 'bugcheck' in entry['message'].lower()
        ]
        kernel_power_41_entries = [
            entry for entry in entries
            if entry['provider_name'] == 'Microsoft-Windows-Kernel-Power' and entry['event_id'] == 41
        ]
        live_kernel_entries = [
            entry for entry in entries
            if 'livekernelevent' in entry['message'].lower()
            or entry['provider_name'] == 'Windows Error Reporting'
        ]

        panic_like_event_count = len(entries)
        latest_entry = entries[0]
        repeated_event_keys = {}
        for entry in entries:
            key = f"{entry['provider_name']}:{entry['event_id']}"
            repeated_event_keys[key] = repeated_event_keys.get(key, 0) + 1
        repeated_events = [
            f"{key}({count})"
            for key, count in repeated_event_keys.items()
            if count > 1
        ]

        if panic_like_event_count > max_panic_like_event_count:
            return self.fail(
                '커널 패닉 유사 이벤트 감지',
                message='최근 30일 내 커널 패닉 유사 이벤트가 기준치를 초과했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        return self.ok(
            metrics={
                'panic_like_event_count': panic_like_event_count,
                'bugcheck_event_count': len(bugcheck_entries),
                'kernel_power_41_count': len(kernel_power_41_entries),
                'live_kernel_event_count': len(live_kernel_entries),
                'latest_event_time': latest_entry['time_created'],
                'latest_event_provider': latest_entry['provider_name'],
                'latest_event_id': latest_entry['event_id'],
                'repeated_events': repeated_events,
                'matched_failure_keywords': matched_failure_keywords,
            },
            thresholds={
                'max_panic_like_event_count': max_panic_like_event_count,
                'failure_keywords': failure_keywords,
            },
            reasons='최근 30일 내 커널 패닉 유사 이벤트 수가 기준 범위 내입니다.',
            message='Windows 커널 로그 점검이 정상 수행되었습니다.',
        )


CHECK_CLASS = Check
