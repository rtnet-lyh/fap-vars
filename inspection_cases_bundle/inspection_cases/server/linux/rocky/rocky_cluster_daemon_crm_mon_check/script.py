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
