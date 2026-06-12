# -*- coding: utf-8 -*-

import json

from .common._base import BaseCheck


NETWORK_LINK_STATUS_COMMAND = (
    "$OutputEncoding = [System.Text.UTF8Encoding]::new($false); "
    "[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); "
    "Get-NetAdapter -Physical | "
    "Select-Object Name, InterfaceDescription, Status, LinkSpeed | "
    "ConvertTo-Json -Depth 3"
)

STATUS_MAP = {
    'up': 'Up',
    'down': 'Down',
    'unknown': 'Unknown',
    'not present': 'Not Present',
}


def _normalize_status(value):
    return STATUS_MAP.get(str(value).strip().lower(), str(value).strip())


def _parse_adapter_entry(entry):
    if not isinstance(entry, dict):
        return None

    name = str(entry.get('Name', '')).strip()
    interface_description = str(entry.get('InterfaceDescription', '')).strip()
    status = _normalize_status(entry.get('Status', ''))
    link_speed = str(entry.get('LinkSpeed', '')).strip()

    if not name and not interface_description and not status and not link_speed:
        return None

    return {
        'name': name,
        'interface_description': interface_description,
        'status': status,
        'link_speed': link_speed,
    }


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'winrm'
    WINRM_SHELL = 'powershell'

    def run(self):
        min_up_physical_nic_count = self.get_threshold_var('min_up_physical_nic_count', default=1, value_type='int')
        failure_keywords_raw = self.get_threshold_var('failure_keywords', default='', value_type='str')

        rc, out, err = self._run_ps(NETWORK_LINK_STATUS_COMMAND)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'WinRM 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if self._is_not_applicable(rc, err):
            return self.fail(
                'WinRM 실행 환경을 사용할 수 없습니다.',
                message='Windows NIC 링크 상태 점검을 수행할 수 없습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='Windows 네트워크 링크 상태 점검 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        text = (out or '').strip()
        if not text:
            return self.fail(
                '물리 NIC 정보 없음',
                message='물리 NIC 링크 상태 결과가 비어 있습니다.',
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
                '물리 NIC 실패 키워드 감지',
                message='물리 NIC 링크 상태 결과에서 실패 키워드가 확인되었습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return self.fail(
                '물리 NIC 파싱 실패',
                message='물리 NIC 링크 상태 JSON을 해석하지 못했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        if isinstance(parsed, dict):
            parsed = [parsed]
        elif not isinstance(parsed, list):
            parsed = []

        adapters = []
        for entry in parsed:
            adapter = _parse_adapter_entry(entry)
            if adapter:
                adapters.append(adapter)

        if not adapters:
            return self.fail(
                '물리 NIC 파싱 실패',
                message='물리 NIC 링크 상태 테이블을 해석하지 못했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        up_adapters = [adapter for adapter in adapters if adapter['status'] == 'Up']
        down_adapters = [adapter for adapter in adapters if adapter['status'] == 'Down']
        unknown_adapters = [adapter for adapter in adapters if adapter['status'] == 'Unknown']
        not_present_adapters = [adapter for adapter in adapters if adapter['status'] == 'Not Present']

        if len(up_adapters) < min_up_physical_nic_count:
            return self.fail(
                '활성 물리 NIC 부족',
                message='Up 상태의 물리 NIC 수가 기준치 미만입니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        if down_adapters:
            return self.fail(
                '물리 NIC Down 상태 감지',
                message='Down 상태의 물리 NIC가 확인되었습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        if unknown_adapters:
            return self.fail(
                '물리 NIC Unknown 상태 감지',
                message='상태를 식별하지 못한 물리 NIC가 확인되었습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        reasons = '물리 NIC의 링크 상태를 점검한 결과 Up 상태의 어댑터가 확인되었고 비정상 상태는 없습니다.'
        if not_present_adapters:
            reasons = 'Up 상태의 물리 NIC가 확인되며, 일부 물리 NIC는 현재 장치에 존재하지 않는 상태로 표시됩니다.'

        return self.ok(
            metrics={
                'physical_nic_count': len(adapters),
                'up_physical_nic_count': len(up_adapters),
                'down_physical_nic_count': len(down_adapters),
                'unknown_physical_nic_count': len(unknown_adapters),
                'not_present_physical_nic_count': len(not_present_adapters),
                'up_nic_names': [adapter['name'] for adapter in up_adapters],
                'not_present_nic_names': [adapter['name'] for adapter in not_present_adapters],
                'link_speeds': {
                    adapter['name']: adapter['link_speed']
                    for adapter in adapters
                },
                'matched_failure_keywords': matched_failure_keywords,
            },
            thresholds={
                'min_up_physical_nic_count': min_up_physical_nic_count,
                'failure_keywords': failure_keywords,
            },
            reasons=reasons,
            message=(
                f'Windows 네트워크 링크 상태 점검이 정상입니다. 현재 상태: '
                f'물리 NIC {len(adapters)}개, Up {len(up_adapters)}개 '
                f'(기준 {min_up_physical_nic_count}개 이상), '
                f'Not Present {len(not_present_adapters)}개.'
            ),
        )


CHECK_CLASS = Check
