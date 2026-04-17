# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


LOG_FAN_COMMAND = (
    "$f=Get-CimInstance Win32_Fan -ErrorAction SilentlyContinue; "
    "$e=Get-WinEvent -FilterHashtable @{LogName='System';StartTime=(Get-Date).AddDays(-30);Level=@(1,2,3)} -ErrorAction SilentlyContinue | "
    "Where-Object { $_.Message -match '(?i)\\bfan\\b|fan fail|cooling|thermal|overheat|fan speed too low|failure detected' }; "
    "if($f){$f | Select-Object Name,Status,DesiredSpeed,VariableSpeed,Availability,ConfigManagerErrorCode | Format-Table -Auto} else {'No Win32_Fan data exposed by firmware/driver.'}; "
    "if($e){$e | Select-Object -First 50 TimeCreated,ProviderName,Id,LevelDisplayName,@{N='Message';E={($_.Message -replace '\\r?\\n',' ')}} | Format-Table -Wrap -Auto} else {'No fan-related warning/error events found in the last 30 days.'}"
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
            return self.not_applicable(
                'WinRM 실행 환경을 사용할 수 없습니다.',
                raw_output=(err or '').strip(),
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

        lines = [line.rstrip() for line in text.splitlines() if line.strip()]
        no_fan_data = 'No Win32_Fan data exposed by firmware/driver.' in text
        no_event_data = 'No fan-related warning/error events found in the last 30 days.' in text

        fan_entries = []
        event_entries = []
        in_fan_table = False
        in_event_table = False
        for line in lines:
            stripped = line.strip()

            if stripped == 'No Win32_Fan data exposed by firmware/driver.':
                in_fan_table = False
                continue
            if stripped == 'No fan-related warning/error events found in the last 30 days.':
                in_event_table = False
                continue

            if stripped.startswith('Name') and 'ConfigManagerErrorCode' in stripped:
                in_fan_table = True
                in_event_table = False
                continue
            if stripped.startswith('TimeCreated') and 'ProviderName' in stripped:
                in_event_table = True
                in_fan_table = False
                continue
            if stripped.startswith('----') or stripped.startswith('-----------'):
                continue

            if in_event_table:
                match = EVENT_PATTERN.match(stripped)
                if match:
                    event_entries.append({
                        'time_created': match.group('time'),
                        'provider_name': match.group('provider').strip(),
                        'event_id': _parse_int(match.group('id')),
                        'level': match.group('level').strip(),
                        'message': match.group('message').strip(),
                    })
                continue

            if in_fan_table:
                parts = re.split(r'\s{2,}', stripped)
                if not parts:
                    continue
                fan_entries.append({
                    'name': parts[0].strip(),
                    'status': parts[1].strip() if len(parts) > 1 else '',
                    'desired_speed': parts[2].strip() if len(parts) > 2 else '',
                    'variable_speed': parts[3].strip() if len(parts) > 3 else '',
                    'availability': parts[4].strip() if len(parts) > 4 else '',
                    'config_manager_error_code': parts[5].strip() if len(parts) > 5 else '',
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

        if abnormal_fan_entries:
            return self.fail(
                'FAN 장치 상태 이상 감지',
                message='FAN 장치 상태가 정상 범위를 벗어났습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        if len(event_entries) > max_fan_event_count:
            return self.fail(
                'FAN 로그 이벤트 감지',
                message='최근 30일 내 FAN 관련 경고/오류 이벤트가 기준치를 초과했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        latest_event = event_entries[0] if event_entries else {}

        reasons = 'FAN 장치 상태와 최근 30일 이벤트 로그를 점검한 결과 이상 징후가 없습니다.'
        if no_fan_data and no_event_data:
            reasons = 'Win32_Fan 장치 정보는 노출되지 않았지만 최근 30일 내 FAN 관련 경고/오류 이벤트는 확인되지 않았습니다.'
        elif no_fan_data:
            reasons = 'Win32_Fan 장치 정보는 노출되지 않았지만 FAN 관련 이벤트 수는 기준 범위 내입니다.'
        elif fan_entries and not event_entries:
            reasons = 'FAN 장치 상태는 정상이며 최근 30일 내 FAN 관련 경고/오류 이벤트가 없습니다.'

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
            message='Windows FAN 로그 점검이 정상 수행되었습니다.',
        )


CHECK_CLASS = Check
