# -*- coding: utf-8 -*-

import json

from .common._base import BaseCheck


LOG_NIC_COMMAND = (
    "$OutputEncoding = [System.Text.UTF8Encoding]::new($false); "
    "[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); "
    "$nic=Get-NetAdapter -IncludeHidden -ErrorAction SilentlyContinue | "
    "Select-Object Name,InterfaceDescription,Status,LinkSpeed,MacAddress,ifIndex; "
    "$events=Get-WinEvent -FilterHashtable @{LogName='System';StartTime=(Get-Date).AddDays(-30);Level=@(1,2,3)} -ErrorAction SilentlyContinue | "
    "Where-Object { "
    "$_.ProviderName -match '(?i)ndis|netwtw|e1d|e1iexpress|e1rexpress|b57nd60a|bnx|mlx|netadaptercx|tcpip' -or "
    "$_.Message -match '(?i)\\bnic\\b|network adapter|link down|link up|media disconnected|media connected|network link is disconnected|network link has been established|disconnected from the network|connected to the network|adapter reset|network interface.*down|network interface.*up|status down|status up|failover' "
    "} | "
    "Sort-Object TimeCreated -Descending | "
    "Select-Object -First 50 @{N='TimeCreated';E={$_.TimeCreated.ToString('yyyy-MM-dd HH:mm:ss')}},ProviderName,Id,LevelDisplayName,@{N='Message';E={($_.Message -replace '\\r?\\n',' ')}}; "
    "$payload=[pscustomobject]@{NicStatus=@($nic);RecentEvents=@($events)}; "
    "$payload | ConvertTo-Json -Depth 5 -Compress"
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
    'vmware',
    'vpn adapter',
    'anyconnect',
    'fortinet virtual',
    'wsl',
)

NEGATIVE_EVENT_PATTERNS = (
    'link down',
    'media disconnected',
    'network link is disconnected',
    'disconnected from the network',
    'status down',
    'failover',
    'adapter reset',
)

POSITIVE_EVENT_PATTERNS = (
    'link up',
    'media connected',
    'network link has been established',
    'connected to the network',
    'status up',
)


def _normalize_status(value):
    return STATUS_MAP.get(str(value).strip().lower(), str(value).strip())


def _normalize_payload(raw_text):
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError:
        return None

    if not isinstance(payload, dict):
        return None

    adapters = []
    events = []

    for row in payload.get('NicStatus') or []:
        if not isinstance(row, dict):
            continue
        adapters.append({
            'name': str(row.get('Name', '')).strip(),
            'interface_description': str(row.get('InterfaceDescription', '')).strip(),
            'status': _normalize_status(row.get('Status', '')),
            'link_speed': str(row.get('LinkSpeed', '')).strip(),
            'mac_address': str(row.get('MacAddress', '')).strip(),
            'if_index': row.get('ifIndex', ''),
        })

    for row in payload.get('RecentEvents') or []:
        if not isinstance(row, dict):
            continue
        event_id = row.get('Id', '')
        try:
            event_id = int(event_id) if event_id != '' else ''
        except (TypeError, ValueError):
            event_id = ''
        events.append({
            'time_created': str(row.get('TimeCreated', '')).strip(),
            'provider_name': str(row.get('ProviderName', '')).strip(),
            'event_id': event_id,
            'level': str(row.get('LevelDisplayName', '')).strip(),
            'message': str(row.get('Message', '')).strip(),
        })

    return adapters, events


def _is_ignored_adapter(adapter):
    haystack = ' '.join([
        adapter.get('name', ''),
        adapter.get('interface_description', ''),
    ]).lower()
    return any(keyword in haystack for keyword in IGNORED_ADAPTER_KEYWORDS)


def _contains_any(text, patterns):
    lowered = text.lower()
    return any(pattern in lowered for pattern in patterns)


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
            return self.fail(
                'WinRM 실행 환경을 사용할 수 없습니다.',
                message='Windows NIC 로그 점검을 수행할 수 없습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
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

        parsed = _normalize_payload(text)
        if parsed is None:
            return self.fail(
                'NIC 로그 파싱 실패',
                message='NIC 상태 또는 이벤트 JSON 결과를 해석하지 못했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        adapters, event_entries = parsed
        if not adapters:
            return self.fail(
                'NIC 상태 파싱 실패',
                message='NIC 상태 정보를 확인하지 못했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        failure_keywords = [
            keyword.strip()
            for keyword in failure_keywords_raw.split(',')
            if keyword.strip()
        ]
        serialized_text = json.dumps({
            'NicStatus': adapters,
            'RecentEvents': event_entries,
        }, ensure_ascii=False)
        matched_failure_keywords = [
            keyword for keyword in failure_keywords if keyword.lower() in serialized_text.lower()
        ]
        if matched_failure_keywords:
            return self.fail(
                'NIC 로그 실패 키워드 감지',
                message=f'NIC 로그 결과에서 실패 키워드가 확인되었습니다. 실패 키워드: {json.dumps(matched_failure_keywords)}',
                stdout=serialized_text,
                stderr=(err or '').strip(),
            )

        service_adapters = [adapter for adapter in adapters if not _is_ignored_adapter(adapter)]
        all_up_adapters = [adapter for adapter in adapters if adapter['status'] == 'Up']
        up_service_adapters = [adapter for adapter in service_adapters if adapter['status'] == 'Up']
        down_service_adapters = [
            adapter for adapter in service_adapters
            if adapter['status'] in ('Disconnected', 'Disabled', 'Not Present')
        ]
        effective_up_adapters = up_service_adapters if service_adapters else all_up_adapters

        negative_event_entries = [
            entry for entry in event_entries
            if _contains_any(entry['message'], NEGATIVE_EVENT_PATTERNS)
        ]
        positive_event_entries = [
            entry for entry in event_entries
            if _contains_any(entry['message'], POSITIVE_EVENT_PATTERNS)
        ]
        failover_event_entries = [
            entry for entry in event_entries
            if 'failover' in entry['message'].lower()
        ]
        disconnect_event_entries = [
            entry for entry in event_entries
            if _contains_any(entry['message'], ('link down', 'media disconnected', 'disconnected from the network', 'status down'))
        ]

        if len(effective_up_adapters) < min_up_nic_count:
            return self.fail(
                '활성 NIC 부족',
                message=(
                    f'Windows NIC 로그 점검에 실패했습니다. 현재 상태: '
                    f'Up 상태 NIC {len(effective_up_adapters)}개로 기준 {min_up_nic_count}개 미만입니다. '
                    f'비활성 서비스 NIC: {", ".join(adapter["name"] for adapter in down_service_adapters) if down_service_adapters else "없음"}.'
                ),
                stdout=serialized_text,
                stderr=(err or '').strip(),
            )

        if len(negative_event_entries) > max_nic_event_count:
            return self.fail(
                'NIC 링크 이상 이벤트 감지',
                message=(
                    f'Windows NIC 로그 점검에 실패했습니다. 현재 상태: '
                    f'부정 이벤트 {len(negative_event_entries)}건 (기준 {max_nic_event_count}건 이하), '
                    f'link/media down {len(disconnect_event_entries)}건, failover {len(failover_event_entries)}건. '
                    f'NIC 링크 및 이중화 구성을 점검해야 합니다.'
                ),
                stdout=serialized_text,
                stderr=(err or '').strip(),
            )

        latest_event = event_entries[0] if event_entries else {}
        reasons = (
            '서비스 NIC 중 Up 상태 인터페이스가 기준 이상이며, 최근 30일 내 '
            'NIC link down/media disconnected/failover 같은 장애성 이벤트가 허용 범위 이내입니다.'
        )
        if down_service_adapters and not negative_event_entries:
            reasons = (
                '서비스 NIC 중 Up 상태 인터페이스가 기준 이상입니다. 일부 비활성 NIC가 있으나 최근 30일 내 '
                '장애성 NIC 이벤트는 확인되지 않았습니다.'
            )

        return self.ok(
            metrics={
                'nic_count': len(adapters),
                'service_nic_count': len(service_adapters),
                'up_nic_count': len(all_up_adapters),
                'up_service_nic_count': len(up_service_adapters),
                'inactive_service_nic_count': len(down_service_adapters),
                'ignored_nic_count': len(adapters) - len(service_adapters),
                'nic_event_count': len(event_entries),
                'negative_nic_event_count': len(negative_event_entries),
                'positive_nic_event_count': len(positive_event_entries),
                'failover_event_count': len(failover_event_entries),
                'disconnect_event_count': len(disconnect_event_entries),
                'active_nic_names': [adapter['name'] for adapter in effective_up_adapters],
                'inactive_service_nic_names': [adapter['name'] for adapter in down_service_adapters],
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
            message=(
                f'Windows NIC 로그 점검이 정상입니다. 현재 상태: '
                f'NIC {len(adapters)}개, 서비스 NIC {len(service_adapters)}개, '
                f'Up {len(effective_up_adapters)}개 (기준 {min_up_nic_count}개 이상), '
                f'부정 이벤트 {len(negative_event_entries)}건 (기준 {max_nic_event_count}건 이하), '
                f'양호 이벤트 {len(positive_event_entries)}건.'
            ),
        )


CHECK_CLASS = Check
