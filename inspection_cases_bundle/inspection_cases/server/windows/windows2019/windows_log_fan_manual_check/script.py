# -*- coding: utf-8 -*-

import json

from .common._base import BaseCheck


LOG_FAN_COMMAND = (
    "$OutputEncoding = [System.Text.UTF8Encoding]::new($false); "
    "[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); "
    "$f=Get-CimInstance Win32_Fan -ErrorAction SilentlyContinue; "
    "$e=Get-WinEvent -FilterHashtable @{LogName='System';StartTime=(Get-Date).AddDays(-30);Level=@(1,2,3)} -ErrorAction SilentlyContinue | "
    "Where-Object { $_.Message -match '(?i)\\bfan\\b|fan fail|cooling|thermal|overheat|fan speed too low|failure detected' }; "
    "$result=[ordered]@{"
    "FanDataExposed=[bool]$f; "
    "EventDataExposed=[bool]$e; "
    "Fans=@($f | Select-Object Name,Status,DesiredSpeed,VariableSpeed,Availability,ConfigManagerErrorCode); "
    "Events=@($e | Select-Object -First 50 TimeCreated,ProviderName,Id,LevelDisplayName,@{N='Message';E={($_.Message -replace '\\r?\\n',' ')}})"
    "}; "
    "$result | ConvertTo-Json -Depth 4"
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
        max_fan_event_count = self.get_threshold_var('max_fan_event_count', default=0, value_type='int')
        failure_keywords_raw = self.get_threshold_var('failure_keywords', default='', value_type='str')

        rc, out, err = self._run_ps(LOG_FAN_COMMAND)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'WinRM 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if self._is_not_applicable(rc, err):
            return self.fail(
                'WinRM 실행 환경을 사용할 수 없습니다.',
                message='Windows FAN 로그 점검을 수행할 수 없습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='Windows FAN 로그 점검 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        text = (out or '').strip()
        if not text:
            return self.fail(
                'FAN 로그 출력 없음',
                message='FAN 장치 또는 이벤트 로그 점검 결과가 비어 있습니다.',
                stdout='',
                stderr=(err or '').strip(),
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
                'FAN 로그 실패 키워드 감지',
                message='FAN 로그 결과에서 실패 키워드가 확인되었습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return self.fail(
                'FAN 로그 파싱 실패',
                message='FAN 장치 또는 이벤트 로그 JSON을 해석하지 못했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        no_fan_data = not bool(parsed.get('FanDataExposed')) if isinstance(parsed, dict) else True
        no_event_data = not bool(parsed.get('EventDataExposed')) if isinstance(parsed, dict) else True

        fan_entries = []
        for entry in _as_list(parsed.get('Fans', [])) if isinstance(parsed, dict) else []:
            if not isinstance(entry, dict):
                continue
            fan_entries.append({
                'name': str(entry.get('Name', '')).strip(),
                'status': str(entry.get('Status', '')).strip(),
                'desired_speed': str(entry.get('DesiredSpeed', '')).strip(),
                'variable_speed': str(entry.get('VariableSpeed', '')).strip(),
                'availability': str(entry.get('Availability', '')).strip(),
                'config_manager_error_code': str(entry.get('ConfigManagerErrorCode', '')).strip(),
            })

        event_entries = []
        for entry in _as_list(parsed.get('Events', [])) if isinstance(parsed, dict) else []:
            if not isinstance(entry, dict):
                continue
            event_id = entry.get('Id', '')
            event_entries.append({
                'time_created': str(entry.get('TimeCreated', '')).strip(),
                'provider_name': str(entry.get('ProviderName', '')).strip(),
                'event_id': _parse_int(event_id) if str(event_id).strip() else '',
                'level': str(entry.get('LevelDisplayName', '')).strip(),
                'message': str(entry.get('Message', '')).strip(),
            })

        abnormal_fan_entries = []
        for entry in fan_entries:
            status = entry['status'].lower()
            config_error = entry['config_manager_error_code']
            if status and status not in ('ok', 'operating normally'):
                abnormal_fan_entries.append(entry)
                continue
            if config_error and config_error not in ('0', ''):
                abnormal_fan_entries.append(entry)

        if len(event_entries) > max_fan_event_count:
            return self.fail(
                'FAN 로그 이벤트 감지',
                message='최근 30일 내 FAN 관련 경고/오류 이벤트가 기준치를 초과했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        latest_event = event_entries[0] if event_entries else {}

        reasons = '최근 30일 FAN/냉각 관련 이벤트 로그를 점검한 결과 이상 징후가 없습니다.'
        if no_event_data:
            reasons = '최근 30일 내 FAN 관련 경고/오류 이벤트가 없습니다.'
        if no_fan_data and no_event_data:
            reasons = 'Win32_Fan 장치 정보 노출 여부와 무관하게 최근 30일 내 FAN 관련 경고/오류 이벤트가 없습니다.'

        return self.ok(
            metrics={
                'fan_device_count': len(fan_entries),
                'abnormal_fan_count': len(abnormal_fan_entries),
                'fan_event_count': len(event_entries),
                'fan_data_exposed': not no_fan_data,
                'latest_event_time': latest_event.get('time_created', ''),
                'latest_event_provider': latest_event.get('provider_name', ''),
                'latest_event_id': latest_event.get('event_id', ''),
                'matched_failure_keywords': matched_failure_keywords,
            },
            thresholds={
                'max_fan_event_count': max_fan_event_count,
                'failure_keywords': failure_keywords,
            },
            reasons=reasons,
            message=(
                f'Windows FAN 로그 점검이 정상입니다. 현재 상태: \n'
                f'FAN 관련 이벤트 {len(event_entries)}건 (기준 {max_fan_event_count}건 이하), \n'
                f'FAN 장치 정보 {len(fan_entries)}개, 비정상으로 해석된 장치 {len(abnormal_fan_entries)}개 및 {json.dumps(abnormal_fan_entries)} \n'
                f'Win32_Fan 노출 여부 {not no_fan_data}, '
                f'최근 이벤트 ID {latest_event.get("event_id", "N/A")}.'
            ),
        )


CHECK_CLASS = Check
