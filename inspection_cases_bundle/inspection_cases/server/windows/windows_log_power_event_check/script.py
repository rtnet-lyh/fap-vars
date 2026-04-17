# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


LOG_POWER_COMMAND = (
    "$e=Get-WinEvent -FilterHashtable @{LogName='System';StartTime=(Get-Date).AddDays(-30);Level=@(1,2,3)} -ErrorAction SilentlyContinue | "
    "Where-Object { $_.ProviderName -in @('Microsoft-Windows-Kernel-Power','Microsoft-Windows-WHEA-Logger','Microsoft-Windows-Kernel-Boot','ACPI') -or $_.Message -match '(?i)\\bpsu\\b|power supply|ps failed|failure detected|malfunction|voltage|power fault|power failure' }; "
    "if($e){$e | Select-Object TimeCreated,ProviderName,Id,LevelDisplayName,@{N='Message';E={($_.Message -replace '\\r?\\n',' ')}} | Format-Table -Wrap -Auto}else{'No PSU/power-failure-like warning or error events found in the last 30 days.'}"
)

EVENT_PATTERN = re.compile(
    r'^(?P<time>\d{4}-\d{2}-\d{2}\s+(?:오전|오후)\s+\d{1,2}:\d{2}:\d{2})\s+'
    r'(?P<provider>.+?)\s+'
    r'(?P<id>\d+)\s+'
    r'(?P<level>오류|경고|정보|Error|Warning|Critical|Information)\s+'
    r'(?P<message>.+)$'
)


def _parse_int(value):
    return int(str(value).strip())


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'winrm'
    WINRM_SHELL = 'powershell'

    def run(self):
        max_power_event_count = self.get_threshold_var('max_power_event_count', default=0, value_type='int')
        failure_keywords_raw = self.get_threshold_var('failure_keywords', default='', value_type='str')

        rc, out, err = self._run_ps(LOG_POWER_COMMAND)

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
                message='Windows POWER 로그 점검 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        text = (out or '').strip()
        if not text or 'No PSU/power-failure-like warning or error events found in the last 30 days.' in text:
            return self.ok(
                metrics={
                    'power_event_count': 0,
                    'kernel_power_41_count': 0,
                    'power_fault_event_count': 0,
                    'bugcheck_zero_or_missing_count': 0,
                    'matched_failure_keywords': [],
                },
                thresholds={
                    'max_power_event_count': max_power_event_count,
                    'failure_keywords': [],
                },
                reasons='최근 30일 내 PSU/전원 장애 관련 이벤트가 확인되지 않았습니다.',
                message='Windows POWER 로그 점검이 정상 수행되었습니다.',
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
                'POWER 로그 실패 키워드 감지',
                message='POWER 로그 결과에서 실패 키워드가 확인되었습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        lines = [line.rstrip() for line in text.splitlines() if line.strip()]
        entries = []
        for line in lines:
            if line.startswith('TimeCreated') or line.startswith('-----------') or line.lstrip().startswith('---'):
                continue
            match = EVENT_PATTERN.match(line)
            if not match:
                continue
            entries.append({
                'time_created': match.group('time'),
                'provider_name': match.group('provider').strip(),
                'event_id': _parse_int(match.group('id')),
                'level': match.group('level').strip(),
                'message': match.group('message').strip(),
            })

        if not entries:
            return self.fail(
                'POWER 로그 파싱 실패',
                message='전원 관련 이벤트 항목을 해석하지 못했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        kernel_power_41_entries = [
            entry for entry in entries
            if entry['provider_name'] == 'Microsoft-Windows-Kernel-Power' and entry['event_id'] == 41
        ]
        power_fault_entries = [
            entry for entry in entries
            if re.search(r'(?i)\bpsu\b|power supply|ps failed|failure detected|malfunction|voltage|power fault|power failure', entry['message'])
        ]
        bugcheck_zero_or_missing_entries = [
            entry for entry in kernel_power_41_entries
            if re.search(r'(?i)bugcheck', entry['message']) and re.search(r'(?i)(0x0+\b|0\b|없음|none)', entry['message'])
        ]

        repeated_event_keys = {}
        for entry in entries:
            key = f"{entry['provider_name']}:{entry['event_id']}"
            repeated_event_keys[key] = repeated_event_keys.get(key, 0) + 1
        repeated_events = [
            f"{key}({count})"
            for key, count in repeated_event_keys.items()
            if count > 1
        ]

        latest_entry = entries[0]

        if len(entries) > max_power_event_count:
            return self.fail(
                '전원 장애 로그 이벤트 감지',
                message='최근 30일 내 PSU/전원 장애 관련 이벤트가 기준치를 초과했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        return self.ok(
            metrics={
                'power_event_count': len(entries),
                'kernel_power_41_count': len(kernel_power_41_entries),
                'power_fault_event_count': len(power_fault_entries),
                'bugcheck_zero_or_missing_count': len(bugcheck_zero_or_missing_entries),
                'latest_event_time': latest_entry['time_created'],
                'latest_event_provider': latest_entry['provider_name'],
                'latest_event_id': latest_entry['event_id'],
                'repeated_events': repeated_events,
                'matched_failure_keywords': matched_failure_keywords,
            },
            thresholds={
                'max_power_event_count': max_power_event_count,
                'failure_keywords': failure_keywords,
            },
            reasons='최근 30일 내 PSU/전원 장애 관련 이벤트 수가 기준 범위 내입니다.',
            message='Windows POWER 로그 점검이 정상 수행되었습니다.',
        )


CHECK_CLASS = Check
