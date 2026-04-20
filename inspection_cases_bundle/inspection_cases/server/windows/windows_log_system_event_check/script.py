# -*- coding: utf-8 -*-

import json

from .common._base import BaseCheck


LOG_SYSTEM_COMMAND = (
    "$OutputEncoding = [System.Text.UTF8Encoding]::new($false); "
    "[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); "
    "Get-WinEvent -FilterHashtable @{LogName=@('System','Application','Security'); "
    "StartTime=(Get-Date).AddDays(-7); Level=@(1,2,3)} -ErrorAction SilentlyContinue | "
    "Where-Object { $_.Message -match '(?i)kernel|hardware|machine check|disk|filesystem|i/o|corrupt|memory|out of memory|driver|module|network|timeout|connection|service|daemon|security|unauthorized|access denied|failed' } | "
    "Select-Object -First 300 TimeCreated,LogName,ProviderName,Id,LevelDisplayName,@{N='Message';E={($_.Message -replace '\\r?\\n',' ')}} | "
    "ConvertTo-Json -Depth 4"
)


def _parse_int(value):
    return int(str(value).strip())


def _as_list(value):
    if isinstance(value, list):
        return value
    if value in (None, ''):
        return []
    return [value]


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'winrm'
    WINRM_SHELL = 'powershell'

    def run(self):
        max_critical_error_count = self.get_threshold_var('max_critical_error_count', default=0, value_type='int')
        max_warning_count = self.get_threshold_var('max_warning_count', default=10, value_type='int')
        failure_keywords_raw = self.get_threshold_var('failure_keywords', default='', value_type='str')

        rc, out, err = self._run_ps(LOG_SYSTEM_COMMAND)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'WinRM 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if self._is_not_applicable(rc, err):
            return self.fail(
                'WinRM 실행 환경을 사용할 수 없습니다.',
                message='Windows 시스템 로그 점검을 수행할 수 없습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='Windows 시스템 로그 점검 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        text = (out or '').strip()
        if not text:
            return self.ok(
                metrics={
                    'event_count': 0,
                    'critical_error_count': 0,
                    'warning_count': 0,
                    'matched_failure_keywords': [],
                },
                thresholds={
                    'max_critical_error_count': max_critical_error_count,
                    'max_warning_count': max_warning_count,
                    'failure_keywords': [],
                },
                reasons='최근 시스템 로그에서 점검 대상 오류/경고 이벤트가 확인되지 않았습니다.',
                message=(
                    'Windows 시스템 로그 점검이 정상입니다. '
                    '현재 상태: 최근 7일 내 점검 대상 시스템 로그 이벤트가 없어 0건으로 집계했습니다.'
                ),
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
                '시스템 로그 실패 키워드 감지',
                message='시스템 로그 결과에서 실패 키워드가 확인되었습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        try:
            raw_entries = json.loads(text)
        except json.JSONDecodeError:
            return self.fail(
                '시스템 로그 파싱 실패',
                message='시스템 로그 이벤트 JSON을 해석하지 못했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        entries = []
        for entry in _as_list(raw_entries):
            if not isinstance(entry, dict):
                continue
            event_id = entry.get('Id', '')
            entries.append({
                'time_created': str(entry.get('TimeCreated', '')).strip(),
                'log_name': str(entry.get('LogName', '')).strip(),
                'provider_name': str(entry.get('ProviderName', '')).strip(),
                'event_id': _parse_int(event_id) if str(event_id).strip() else 0,
                'level': str(entry.get('LevelDisplayName', '')).strip(),
                'message': str(entry.get('Message', '')).strip(),
            })

        if not entries:
            return self.fail(
                '시스템 로그 파싱 실패',
                message='시스템 로그 이벤트 항목을 해석하지 못했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        critical_error_entries = [
            entry for entry in entries
            if entry['level'].lower() in ('critical', 'error', '오류')
        ]
        warning_entries = [
            entry for entry in entries
            if entry['level'].lower() in ('warning', '경고')
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

        if len(critical_error_entries) > max_critical_error_count:
            return self.fail(
                '시스템 로그 오류 이벤트 임계치 초과',
                message=(
                    f'Windows 시스템 로그 점검에 실패했습니다. 현재 상태: '
                    f'Critical/Error {len(critical_error_entries)}건 '
                    f'(기준 {max_critical_error_count}건 이하), '
                    f'Warning {len(warning_entries)}건.'
                    f'Warning 키워드 {len(warning_entries)}건.: {",".join([entry["message"] for entry in warning_entries])}'
                ),
                stdout=text,
                stderr=(err or '').strip(),
            )

        if len(warning_entries) > max_warning_count:
            return self.fail(
                '시스템 로그 경고 이벤트 임계치 초과',
                message=(
                    f'Windows 시스템 로그 점검에 실패했습니다. 현재 상태: '
                    f'Warning {len(warning_entries)}건 (기준 {max_warning_count}건 이하), '
                    f'Critical/Error {len(critical_error_entries)}건.'
                    f'Warning 키워드 {len(warning_entries)}건.: {",".join([entry["message"] for entry in warning_entries])}'

                ),
                stdout=text,
                stderr=(err or '').strip(),
            )

        return self.ok(
            metrics={
                'event_count': len(entries),
                'critical_error_count': len(critical_error_entries),
                'warning_count': len(warning_entries),
                'latest_event_time': latest_entry['time_created'],
                'latest_event_log_name': latest_entry['log_name'],
                'latest_event_provider': latest_entry['provider_name'],
                'latest_event_id': latest_entry['event_id'],
                'repeated_events': repeated_events,
                'matched_failure_keywords': matched_failure_keywords,
            },
            thresholds={
                'max_critical_error_count': max_critical_error_count,
                'max_warning_count': max_warning_count,
                'failure_keywords': failure_keywords,
            },
            reasons='최근 시스템 로그의 Error/Critical/Warning 이벤트 수가 기준 범위 내입니다.',
            message=(
                f'Windows 시스템 로그 점검이 정상입니다. 현재 상태: '
                f'이벤트 {len(entries)}건, Critical/Error {len(critical_error_entries)}건 '
                f'(기준 {max_critical_error_count}건 이하), Warning {len(warning_entries)}건 '
                f'(기준 {max_warning_count}건 이하), 최신 이벤트 ID {latest_entry["event_id"]}.'
            ),
        )


CHECK_CLASS = Check
