# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


LOG_NIC_COMMAND = (
    "'==NIC Status=='; "
    "Get-NetAdapter -IncludeHidden -ErrorAction SilentlyContinue | "
    "Select-Object Name,InterfaceDescription,Status,LinkSpeed,MacAddress,ifIndex | "
    "Format-Table -Auto; "
    "'==Recent NIC Events=='; "
    "$e=Get-WinEvent -FilterHashtable @{LogName='System';StartTime=(Get-Date).AddDays(-30);Level=@(1,2,3)} "
    "-ErrorAction SilentlyContinue | "
    "Where-Object { $_.Message -match '(?i)\\bnic\\b|network adapter|link down|link up|media disconnected|media connected|status down|status up|failover' }; "
    "if($e){$e | Select-Object -First 50 TimeCreated,ProviderName,Id,LevelDisplayName,@{N='Message';E={($_.Message -replace '\\r?\\n',' ')}} | Format-Table -Wrap -Auto}else{'No NIC link/failover-like warning or error events found in the last 30 days.'}"
)

EVENT_PATTERN = re.compile(
    r'^(?P<time>\d{4}-\d{2}-\d{2}\s+(?:오전|오후)\s+\d{1,2}:\d{2}:\d{2})\s+'
    r'(?P<provider>.+?)\s+'
    r'(?P<id>\d+)\s+'
    r'(?P<level>오류|경고|정보|Error|Warning|Critical|Information)\s+'
    r'(?P<message>.+)$'
)

STATUS_MAP = {
    'up': 'Up',
    'disconnected': 'Disconnected',
    'disabled': 'Disabled',
    'not present': 'Not Present',
}

IGNORED_ADAPTER_KEYWORDS = (
    'wan miniport',
    'wi-fi direct',
    'bluetooth',
    'teredo',
    '6to4',
    'ip-https',
    'kernel debug',
    'pseudo-interface',
    'virtual switch extension adapter',
    'virtual ethernet adapter',
    'hyper-v',
    'vpn',
    'fortinet virtual',
)


def _parse_int(value):
    return int(str(value).strip())


def _normalize_status(value):
    return STATUS_MAP.get(str(value).strip().lower(), str(value).strip())


def _is_mac_address(value):
    return bool(re.match(r'^[0-9A-Fa-f]{2}(?:-[0-9A-Fa-f]{2}){5}$', str(value).strip()))


def _is_ignored_adapter(adapter):
    haystack = ' '.join([
        adapter.get('name', ''),
        adapter.get('interface_description', ''),
    ]).lower()
    return any(keyword in haystack for keyword in IGNORED_ADAPTER_KEYWORDS)


def _parse_adapter_line(line):
    parts = [part.strip() for part in re.split(r'\s{2,}', line.strip()) if part.strip()]
    if not parts:
        return None

    status_index = None
    for index, part in enumerate(parts):
        if part.lower() in STATUS_MAP:
            status_index = index
            break

    if status_index is None:
        return None

    name = parts[0]
    interface_description = ''
    if status_index > 1:
        interface_description = ' '.join(parts[1:status_index])

    status = _normalize_status(parts[status_index])
    remaining = parts[status_index + 1:]

    link_speed = remaining[0] if remaining else ''
    mac_address = ''
    if_index = ''

    for value in remaining[1:]:
        if _is_mac_address(value):
            mac_address = value
            continue
        if re.match(r'^\d+$', value):
            if_index = _parse_int(value)

    return {
        'name': name,
        'interface_description': interface_description,
        'status': status,
        'link_speed': link_speed,
        'mac_address': mac_address,
        'if_index': if_index,
    }


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'winrm'
    WINRM_SHELL = 'powershell'

    def run(self):
        min_up_nic_count = self.get_threshold_var('min_up_nic_count', default=1, value_type='int')
        max_nic_event_count = self.get_threshold_var('max_nic_event_count', default=0, value_type='int')
        failure_keywords_raw = self.get_threshold_var('failure_keywords', default='', value_type='str')

        rc, out, err = self._run_ps(LOG_NIC_COMMAND)

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
                message='Windows NIC 로그 점검 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        text = (out or '').strip()
        if not text:
            return self.fail(
                'NIC 로그 출력 없음',
                message='NIC 상태 또는 이벤트 로그 점검 결과가 비어 있습니다.',
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
                'NIC 로그 실패 키워드 감지',
                message='NIC 로그 결과에서 실패 키워드가 확인되었습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        no_nic_events = 'No NIC link/failover-like warning or error events found in the last 30 days.' in text
        lines = [line.rstrip() for line in text.splitlines() if line.strip()]

        adapters = []
        event_entries = []
        section = None

        for line in lines:
            stripped = line.strip()

            if stripped == '==NIC Status==':
                section = 'nic'
                continue
            if stripped == '==Recent NIC Events==':
                section = 'event'
                continue

            if stripped == 'No NIC link/failover-like warning or error events found in the last 30 days.':
                continue

            if stripped.startswith('----') or stripped.startswith('-----------'):
                continue

            if section == 'nic':
                if stripped.startswith('Name') and 'Status' in stripped:
                    continue
                adapter = _parse_adapter_line(stripped)
                if adapter:
                    adapters.append(adapter)
                continue

            if section == 'event':
                if stripped.startswith('TimeCreated') and 'ProviderName' in stripped:
                    continue
                match = EVENT_PATTERN.match(stripped)
                if match:
                    event_entries.append({
                        'time_created': match.group('time'),
                        'provider_name': match.group('provider').strip(),
                        'event_id': _parse_int(match.group('id')),
                        'level': match.group('level').strip(),
                        'message': match.group('message').strip(),
                    })

        if not adapters:
            return self.fail(
                'NIC 상태 파싱 실패',
                message='NIC 상태 테이블을 해석하지 못했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        service_adapters = [adapter for adapter in adapters if not _is_ignored_adapter(adapter)]
        all_up_adapters = [adapter for adapter in adapters if adapter['status'] == 'Up']
        up_service_adapters = [adapter for adapter in service_adapters if adapter['status'] == 'Up']
        disconnected_service_adapters = [
            adapter for adapter in service_adapters
            if adapter['status'] in ('Disconnected', 'Disabled', 'Not Present')
        ]

        effective_up_adapters = up_service_adapters if service_adapters else all_up_adapters

        if len(effective_up_adapters) < min_up_nic_count:
            return self.fail(
                '활성 NIC 부족',
                message='현재 Up 상태의 서비스 NIC 수가 기준치 미만입니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        if len(event_entries) > max_nic_event_count:
            return self.fail(
                'NIC 링크 이벤트 감지',
                message='최근 30일 내 NIC link/media/failover 관련 경고/오류 이벤트가 기준치를 초과했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        latest_event = event_entries[0] if event_entries else {}

        reasons = '현재 Up 상태의 NIC가 확인되었고 최근 30일 내 NIC link/media/failover 관련 경고/오류 이벤트가 없습니다.'
        if disconnected_service_adapters and no_nic_events:
            reasons = '현재 Up 상태의 서비스 NIC가 확인되며, 일부 비활성 NIC가 있으나 최근 30일 내 NIC link/media/failover 관련 경고/오류 이벤트는 없습니다.'
        elif service_adapters and event_entries:
            reasons = '현재 Up 상태의 서비스 NIC가 확인되며, 최근 30일 이벤트 수는 기준 범위 내입니다.'
        elif not service_adapters:
            reasons = '서비스 NIC 후보는 명확하지 않지만 현재 Up 상태의 NIC가 확인되며 최근 30일 내 관련 경고/오류 이벤트는 없습니다.'

        return self.ok(
            metrics={
                'nic_count': len(adapters),
                'service_nic_count': len(service_adapters),
                'up_nic_count': len(all_up_adapters),
                'up_service_nic_count': len(up_service_adapters),
                'inactive_service_nic_count': len(disconnected_service_adapters),
                'ignored_nic_count': len(adapters) - len(service_adapters),
                'nic_event_count': len(event_entries),
                'active_nic_names': [adapter['name'] for adapter in effective_up_adapters],
                'inactive_service_nic_names': [adapter['name'] for adapter in disconnected_service_adapters],
                'latest_event_time': latest_event.get('time_created', ''),
                'latest_event_provider': latest_event.get('provider_name', ''),
                'latest_event_id': latest_event.get('event_id', ''),
                'matched_failure_keywords': matched_failure_keywords,
            },
            thresholds={
                'min_up_nic_count': min_up_nic_count,
                'max_nic_event_count': max_nic_event_count,
                'failure_keywords': failure_keywords,
            },
            reasons=reasons,
            message='Windows NIC 로그 점검이 정상 수행되었습니다.',
        )


CHECK_CLASS = Check
