# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


LOG_HBA_COMMAND = (
    "'==Initiator Ports=='; "
    "$ip=Get-InitiatorPort -ErrorAction SilentlyContinue; "
    "if($ip){$ip|Select-Object InstanceName,ConnectionType,NodeAddress,PortAddress|Format-Table -Auto}else{'No HBA initiator ports exposed.'}; "
    "'==FC Port State=='; "
    "$fc=Get-CimInstance -Namespace root\\wmi -Class MSFC_FibrePortHBAAttributes -ErrorAction SilentlyContinue; "
    "if($fc){$fc|Select-Object InstanceName,@{N='PortState';E={switch($_.Attributes.PortState){1{'Unknown'}2{'Operational'}3{'User Offline'}4{'Bypassed'}5{'Diagnostics'}6{'Link Down'}7{'Port Error'}8{'Loopback'}default{$_.Attributes.PortState}}}},HBAStatus|Format-Table -Auto}else{'No FC HBA port-state data exposed by driver.'}; "
    "'==Recent HBA Events=='; "
    "$ev=Get-WinEvent -FilterHashtable @{LogName='System';StartTime=(Get-Date).AddDays(-30);Level=@(1,2,3)} -ErrorAction SilentlyContinue|Where-Object{$_.Message -match '(?i)\\bhba\\b|fibre channel|fiber channel|\\bfc\\b|loopback|link down|port.+offline|port.+online'}; "
    "if($ev){$ev|Select-Object -First 50 TimeCreated,ProviderName,Id,LevelDisplayName,@{N='Message';E={($_.Message -replace '\\r?\\n',' ')}}|Format-Table -Wrap -Auto}else{'No HBA/port offline-online-like events found in the last 30 days.'}"
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
        max_hba_event_count = self.get_threshold_var('max_hba_event_count', default=0, value_type='int')
        failure_keywords_raw = self.get_threshold_var('failure_keywords', default='', value_type='str')

        rc, out, err = self._run_ps(LOG_HBA_COMMAND)

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
                message='Windows HBA 로그 점검 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        text = (out or '').strip()
        if not text:
            return self.fail(
                'HBA 로그 출력 없음',
                message='HBA 포트 또는 이벤트 로그 점검 결과가 비어 있습니다.',
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
                'HBA 로그 실패 키워드 감지',
                message='HBA 로그 결과에서 실패 키워드가 확인되었습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        lines = [line.rstrip() for line in text.splitlines() if line.strip()]
        no_initiator_ports = 'No HBA initiator ports exposed.' in text
        no_fc_port_state = 'No FC HBA port-state data exposed by driver.' in text
        no_hba_events = 'No HBA/port offline-online-like events found in the last 30 days.' in text

        initiator_port_count = 0
        fc_port_entries = []
        event_entries = []

        section = None
        for line in lines:
            stripped = line.strip()

            if stripped == '==Initiator Ports==':
                section = 'initiator'
                continue
            if stripped == '==FC Port State==':
                section = 'fc'
                continue
            if stripped == '==Recent HBA Events==':
                section = 'event'
                continue

            if stripped in (
                'No HBA initiator ports exposed.',
                'No FC HBA port-state data exposed by driver.',
                'No HBA/port offline-online-like events found in the last 30 days.',
            ):
                continue

            if stripped.startswith('----') or stripped.startswith('-----------'):
                continue

            if section == 'initiator':
                if stripped.startswith('InstanceName') and 'PortAddress' in stripped:
                    continue
                initiator_port_count += 1
                continue

            if section == 'fc':
                if stripped.startswith('InstanceName') and 'PortState' in stripped:
                    continue
                parts = re.split(r'\s{2,}', stripped)
                if not parts:
                    continue
                fc_port_entries.append({
                    'instance_name': parts[0].strip(),
                    'port_state': parts[1].strip() if len(parts) > 1 else '',
                    'hba_status': parts[2].strip() if len(parts) > 2 else '',
                })
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

        abnormal_port_entries = []
        for entry in fc_port_entries:
            port_state = entry['port_state'].lower()
            hba_status = entry['hba_status'].lower()
            if port_state and port_state not in ('operational', 'loopback'):
                abnormal_port_entries.append(entry)
                continue
            if hba_status and hba_status not in ('hba_status_ok', 'ok', '0'):
                abnormal_port_entries.append(entry)

        if abnormal_port_entries:
            return self.fail(
                'HBA 포트 상태 이상 감지',
                message='HBA 포트 상태 또는 HBAStatus가 정상 범위를 벗어났습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        if len(event_entries) > max_hba_event_count:
            return self.fail(
                'HBA 로그 이벤트 감지',
                message='최근 30일 내 HBA 관련 경고/오류 이벤트가 기준치를 초과했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        latest_event = event_entries[0] if event_entries else {}
        operational_port_count = sum(1 for entry in fc_port_entries if entry['port_state'].lower() == 'operational')
        loopback_port_count = sum(1 for entry in fc_port_entries if entry['port_state'].lower() == 'loopback')

        reasons = 'HBA 포트 상태와 최근 30일 이벤트 로그를 점검한 결과 이상 징후가 없습니다.'
        if no_initiator_ports and no_fc_port_state and no_hba_events:
            reasons = 'HBA initiator 및 FC 포트 상태 정보는 노출되지 않았지만 최근 30일 내 HBA 관련 경고/오류 이벤트는 확인되지 않았습니다.'
        elif (no_initiator_ports or no_fc_port_state) and no_hba_events:
            reasons = '일부 HBA 포트 정보는 노출되지 않았지만 최근 30일 내 HBA 관련 경고/오류 이벤트는 확인되지 않았습니다.'

        return self.ok(
            metrics={
                'initiator_port_count': initiator_port_count,
                'fc_port_count': len(fc_port_entries),
                'operational_port_count': operational_port_count,
                'loopback_port_count': loopback_port_count,
                'abnormal_port_count': len(abnormal_port_entries),
                'hba_event_count': len(event_entries),
                'initiator_ports_exposed': not no_initiator_ports,
                'fc_port_state_exposed': not no_fc_port_state,
                'latest_event_time': latest_event.get('time_created', ''),
                'latest_event_provider': latest_event.get('provider_name', ''),
                'latest_event_id': latest_event.get('event_id', ''),
                'matched_failure_keywords': matched_failure_keywords,
            },
            thresholds={
                'max_hba_event_count': max_hba_event_count,
                'failure_keywords': failure_keywords,
            },
            reasons=reasons,
            message='Windows HBA 로그 점검이 정상 수행되었습니다.',
        )


CHECK_CLASS = Check
