# -*- coding: utf-8 -*-

import json

from .common._base import BaseCheck


OS_HBA_LINK_STATUS_COMMAND = (
    "$OutputEncoding = [System.Text.UTF8Encoding]::new($false); "
    "[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); "
    "if (Get-CimClass -Namespace root\\WMI -ClassName MSFC_FibrePortHBAAttributes -ErrorAction SilentlyContinue) { "
    "Get-CimInstance -Namespace root\\WMI -ClassName MSFC_FibrePortHBAAttributes | "
    "Select-Object @{N='fc_portname';E={(($_.Attributes.PortWWN | ForEach-Object { '{0:X2}' -f $_ }) -join '')}}, "
    "@{N='fc_node_name';E={(($_.Attributes.NodeWWN | ForEach-Object { '{0:X2}' -f $_ }) -join '')}}, "
    "@{N='fc_state';E={switch ($_.Attributes.PortState) { 2 {'Online'} 3 {'Offline'} 6 {'Link Down'} 7 {'Error'} default { \"State:$($_.Attributes.PortState)\" } }}}, "
    "@{N='fc_speed';E={switch ($_.Attributes.PortSpeed) { 0 {'Unknown'} 1 {'1 Gbps'} 2 {'2 Gbps'} 4 {'10 Gbps'} 8 {'4 Gbps'} 9 {'Not Negotiated'} default { \"Raw:$($_.Attributes.PortSpeed)\" } }}} | "
    "ConvertTo-Json -Depth 3 } else { 'FC HBA WMI class not found' }"
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
        max_non_online_port_count = self.get_threshold_var('max_non_online_port_count', default=0, value_type='int')
        failure_keywords_raw = self.get_threshold_var('failure_keywords', default='', value_type='str')

        rc, out, err = self._run_ps(OS_HBA_LINK_STATUS_COMMAND)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'WinRM 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if self._is_not_applicable(rc, err):
            return self.fail(
                'WinRM 실행 환경을 사용할 수 없습니다.',
                message='Windows FC HBA 링크 상태 점검을 수행할 수 없습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='Windows FC HBA 링크 상태 점검 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        text = (out or '').strip()
        if not text or text in ('FC HBA WMI class not found', 'FC HBA 포트 미검출(Windows 기본 Storage provider에서 Fibre Channel 포트를 열거하지 못함)'):
            return self.fail(
                'FC HBA 포트 정보 미검출',
                message='Windows FC HBA 링크 상태 점검에 실패했습니다. 현재 상태: FC HBA 포트 정보를 확인할 수 없습니다.',
                stdout=text,
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
                'FC HBA 실패 키워드 감지',
                message='FC HBA 링크 상태 결과에서 실패 키워드가 확인되었습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        try:
            raw_entries = json.loads(text)
        except json.JSONDecodeError:
            return self.fail(
                'FC HBA 링크 상태 파싱 실패',
                message='FC HBA 포트 상태 JSON을 해석하지 못했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        entries = []
        for entry in _as_list(raw_entries):
            if not isinstance(entry, dict):
                continue
            entries.append({
                'fc_portname': str(entry.get('fc_portname', '')).strip(),
                'fc_node_name': str(entry.get('fc_node_name', '')).strip(),
                'fc_state': str(entry.get('fc_state', '')).strip(),
                'fc_speed': str(entry.get('fc_speed', '')).strip(),
            })

        if not entries:
            return self.fail(
                'FC HBA 링크 상태 파싱 실패',
                message='FC HBA 포트 상태 테이블을 해석하지 못했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        non_online_entries = [
            entry for entry in entries
            if entry['fc_state'].lower() != 'online'
        ]
        invalid_identity_entries = [
            entry for entry in entries
            if not entry['fc_portname'] or not entry['fc_node_name']
        ]

        if invalid_identity_entries:
            return self.fail(
                'FC HBA 식별 정보 이상',
                message='FC HBA 포트 또는 노드 식별 정보가 비어 있습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        if len(non_online_entries) > max_non_online_port_count:
            return self.fail(
                'FC HBA 포트 상태 이상 감지',
                message='Online이 아닌 FC HBA 포트가 기준치를 초과했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        reasons = 'FC HBA 포트가 정상적으로 검출되었고 모든 포트 상태가 Online입니다.'

        return self.ok(
            metrics={
                'fc_hba_exposed': True,
                'fc_port_count': len(entries),
                'online_port_count': len(entries) - len(non_online_entries),
                'non_online_port_count': len(non_online_entries),
                'fc_portnames': [entry['fc_portname'] for entry in entries],
                'fc_node_names': [entry['fc_node_name'] for entry in entries],
                'fc_speeds': [entry['fc_speed'] for entry in entries],
                'matched_failure_keywords': matched_failure_keywords,
            },
            thresholds={
                'max_non_online_port_count': max_non_online_port_count,
                'failure_keywords': failure_keywords,
            },
            reasons=reasons,
            message=(
                f'Windows FC HBA 링크 상태 점검이 정상입니다. 현재 상태: '
                f'포트 {len(entries)}개, Online {len(entries) - len(non_online_entries)}개, '
                f'비정상 {len(non_online_entries)}개 (기준 {max_non_online_port_count}개 이하).'
            ),
        )


CHECK_CLASS = Check
