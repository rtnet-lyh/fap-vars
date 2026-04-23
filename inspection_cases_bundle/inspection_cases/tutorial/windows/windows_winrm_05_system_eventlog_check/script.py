# -*- coding: utf-8 -*-

import json

from .common._base import BaseCheck


SYSTEM_EVENTLOG_COMMAND = (
    "$OutputEncoding = [System.Text.UTF8Encoding]::new($false); "
    "[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); "
    "Get-WinEvent -LogName System -MaxEvents 5 | "
    "Select-Object TimeCreated, Id, LevelDisplayName, ProviderName | "
    "ConvertTo-Json -Depth 4"
)


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
        min_event_count = self.get_threshold_var('min_event_count', default=1, value_type='int')
        rc, out, err = self._run_ps(SYSTEM_EVENTLOG_COMMAND)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'WinRM 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if self._is_not_applicable(rc, err):
            return self.fail(
                'WinRM 실행 환경을 사용할 수 없습니다.',
                message='System 이벤트 로그 튜토리얼을 수행할 수 없습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='System 이벤트 로그 조회 PowerShell 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        text = (out or '').strip()
        if not text:
            return self.fail(
                '출력 파싱 실패',
                message='System 이벤트 로그 결과가 비어 있습니다.',
                stdout='',
                stderr=(err or '').strip(),
            )

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return self.fail(
                '출력 파싱 실패',
                message='System 이벤트 로그 JSON을 해석하지 못했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        events = []
        for entry in _as_list(parsed):
            if not isinstance(entry, dict):
                continue
            event_id = str(entry.get('Id', '')).strip()
            provider_name = str(entry.get('ProviderName', '')).strip()
            if not event_id or not provider_name:
                continue
            events.append({
                'time_created': str(entry.get('TimeCreated', '')).strip(),
                'event_id': event_id,
                'level': str(entry.get('LevelDisplayName', '')).strip(),
                'provider_name': provider_name,
            })

        if len(events) < min_event_count:
            return self.fail(
                '이벤트 수 기준 미달',
                message=(
                    f'확인된 이벤트 수가 기준 미만입니다: '
                    f'{len(events)}건 (기준 {min_event_count}건 이상)'
                ),
                stdout=text,
                stderr=(err or '').strip(),
            )

        latest_event = events[0]

        return self.ok(
            metrics={
                'event_count': len(events),
                'latest_event_id': latest_event['event_id'],
                'latest_provider_name': latest_event['provider_name'],
                'latest_time_created': latest_event['time_created'],
                'events': events,
            },
            thresholds={
                'min_event_count': min_event_count,
            },
            reasons='최근 System 이벤트를 JSON 배열로 정상 수집했습니다.',
            message=(
                '_run_ps 고급 예제가 정상 수행되었습니다. '
                f'event_count={len(events)}, latest_event_id={latest_event["event_id"]}'
            ),
        )


CHECK_CLASS = Check
