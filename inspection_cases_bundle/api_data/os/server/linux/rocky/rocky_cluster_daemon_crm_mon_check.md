# type_name

일상점검

# area_name

server

# category_name

상태점검

# application_type

linux

# application

rocky

# inspection_code


SV-LIN-RKY-001

# is_required

권고

# inspection_name

Cluster 데몬 상태

# inspection_content

Cluster 정상 유무 점검(클러스터의 데몬 Maintenance/Offline 점검)

# inspection_command

```bash
crm_mon -1
```

# inspection_output

```text
Stack: corosync
Current DC: node1 (version 2.1.6-9.el8) - partition with quorum
Last updated: Mon Apr 13 10:15:22 2026
Last change:  Mon Apr 13 10:10:01 2026 by hacluster via crmd on node1

2 nodes configured
3 resource instances configured

Node List:
  * Online: [ node1 node2 ]

Full List of Resources:
  * vip_1     (ocf::heartbeat:IPaddr2):       Started node1
  * web_srv   (systemd:httpd):                Started node1
  * Clone Set: ping-clone [ping]
    * Started: [ node1 node2 ]

Daemon Status:
  corosync: active/enabled
  pacemaker: active/enabled
  pcsd: active/enabled
```

# description

- `crm_mon -1` 명령은 Pacemaker/Corosync 클러스터의 현재 상태를 1회 출력하여 노드, 리소스, 데몬 상태를 확인하는 명령이다.
- `Node List`에서 `Online` 노드 목록과 `OFFLINE` 또는 `Offline` 노드 존재 여부를 확인한다. Offline 노드가 있으면 클러스터 구성원 일부가 정상 참여하지 못하는 상태이므로 장애로 판단한다.
- `Daemon Status`에서 `corosync`, `pacemaker`, `pcsd`가 `active/enabled` 상태인지 확인한다. 데몬이 inactive, disabled, failed 상태이면 클러스터 통신, 리소스 제어, PCS 관리 기능에 문제가 있을 수 있다.
- Maintenance 모드가 표시되는 경우 계획된 작업 여부를 확인한다. 계획되지 않은 Maintenance 상태라면 리소스 자동 복구나 이동이 제한될 수 있으므로 운영자 확인이 필요하다.
- `crm_mon` 명령이 존재하지 않으면 해당 서버는 Pacemaker 클러스터 패키지가 설치되지 않았거나 클러스터 미구성 대상일 수 있으므로 본 항목에서는 성공으로 판단한다.

- **성공**: `crm_mon` 명령이 존재하지 않아 클러스터 미구성 서버로 판단되는 경우
- **성공**: `crm_mon -1` 결과에서 Offline 노드가 확인되지 않는 경우
- **실패**: `crm_mon -1` 결과에서 Offline 노드가 하나 이상 확인되는 경우
- **참고**: Maintenance 상태가 확인되면 계획된 유지보수 여부를 별도로 확인한다. 본 항목의 실패 기준은 Offline 노드 존재 여부를 우선 적용한다.

# thresholds


[]

# inspection_script

# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


CRM_MON_COMMAND = 'crm_mon -1'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def _is_command_not_found(self, rc, stderr):
        if rc == 127:
            return True

        lowered = (stderr or '').lower()
        return any(
            marker in lowered
            for marker in (
                'crm_mon: command not found',
                'crm_mon: not found',
                'no such file or directory',
                'not recognized',
            )
        )

    def _extract_bracket_nodes(self, line):
        match = re.search(r'\[(.*?)\]', line)
        if not match:
            return []

        return [
            token.strip()
            for token in match.group(1).split()
            if token.strip()
        ]

    def _parse_nodes(self, lines):
        online_nodes = []
        offline_nodes = []

        for line in lines:
            lowered = line.lower()
            if re.search(r'\bonline\s*:', lowered):
                online_nodes.extend(self._extract_bracket_nodes(line))
            if re.search(r'\boffline\s*:', lowered):
                offline_nodes.extend(self._extract_bracket_nodes(line))

        return {
            'online_nodes': sorted(set(online_nodes)),
            'offline_nodes': sorted(set(offline_nodes)),
        }

    def _parse_daemon_status(self, lines):
        daemon_status = {}
        in_daemon_status = False

        for line in lines:
            stripped = line.strip()
            if stripped.lower() == 'daemon status:':
                in_daemon_status = True
                continue

            if not in_daemon_status:
                continue
            if not stripped:
                continue
            if not line.startswith((' ', '\t')):
                break

            if ':' not in stripped:
                continue
            name, status = stripped.split(':', 1)
            daemon_status[name.strip()] = status.strip()

        return daemon_status

    def _parse_configured_count(self, lines, label):
        pattern = re.compile(rf'^(\d+)\s+{re.escape(label)}\s+configured$', re.IGNORECASE)
        for line in lines:
            match = pattern.match(line.strip())
            if match:
                return int(match.group(1))
        return None

    def run(self):
        rc, out, err = self._ssh(CRM_MON_COMMAND)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'SSH 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if self._is_command_not_found(rc, err):
            return self.ok(
                metrics={
                    'cluster_configured': False,
                    'crm_mon_available': False,
                    'offline_node_count': 0,
                    'offline_nodes': [],
                },
                thresholds={},
                reasons='crm_mon 명령이 존재하지 않아 클러스터 미구성 서버로 판단했습니다.',
                message='Cluster 데몬 상태 점검 대상이 아닙니다. crm_mon 명령이 없어 클러스터 미구성으로 판단했습니다.',
                raw_output=(err or '').strip(),
            )

        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='crm_mon -1 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        lines = [line.rstrip() for line in (out or '').splitlines()]
        non_empty_lines = [line.strip() for line in lines if line.strip()]
        if not non_empty_lines:
            return self.fail(
                '클러스터 상태 파싱 실패',
                message='crm_mon -1 출력 결과가 비어 있습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        node_metrics = self._parse_nodes(non_empty_lines)
        offline_nodes = node_metrics['offline_nodes']
        daemon_status = self._parse_daemon_status(lines)
        maintenance_detected = any(
            'maintenance' in line.lower()
            for line in non_empty_lines
        )
        metrics = {
            'cluster_configured': True,
            'crm_mon_available': True,
            'node_count_configured': self._parse_configured_count(non_empty_lines, 'nodes'),
            'resource_instance_count_configured': self._parse_configured_count(non_empty_lines, 'resource instances'),
            'online_node_count': len(node_metrics['online_nodes']),
            'online_nodes': node_metrics['online_nodes'],
            'offline_node_count': len(offline_nodes),
            'offline_nodes': offline_nodes,
            'maintenance_detected': maintenance_detected,
            'daemon_status': daemon_status,
            'crm_mon_lines': non_empty_lines,
        }

        if offline_nodes:
            result = self.fail(
                'Offline 클러스터 노드 감지',
                message='crm_mon -1 결과에서 Offline 노드가 확인되었습니다: ' + ', '.join(offline_nodes),
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )
            result['metrics'] = metrics
            result['thresholds'] = {}
            result['reasons'] = 'Offline 노드가 존재하여 클러스터 상태를 실패로 판단했습니다.'
            return result

        maintenance_message = ''
        if maintenance_detected:
            maintenance_message = ' Maintenance 상태가 표시되어 계획 작업 여부 확인이 필요합니다.'

        return self.ok(
            metrics=metrics,
            thresholds={},
            reasons='crm_mon -1 결과에서 Offline 노드가 확인되지 않았습니다.' + maintenance_message,
            message=(
                'Cluster 데몬 상태 점검이 정상 수행되었습니다. '
                f"Online 노드 {len(node_metrics['online_nodes'])}개, Offline 노드 0개."
                + maintenance_message
            ),
        )


CHECK_CLASS = Check
