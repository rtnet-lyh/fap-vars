# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    
    def parse_output(self, output):
        text = str(output or '').replace('\r', '')
        lowered = text.lower()
        command_not_found = any(
            marker in lowered
            for marker in (
                'crm_mon: command not found',
                'crm_mon: not found',
                'command not found: crm_mon',
                'crm_mon: no such file or directory',
                'no such file or directory: crm_mon',
                'crm_mon: not recognized',
            )
        )

        lines = []
        for raw_line in text.splitlines():
            line = raw_line.rstrip()
            stripped = line.strip()
            if not stripped:
                continue
            if stripped == 'crm_mon -1':
                continue
            if stripped.endswith('# crm_mon -1') or stripped.endswith('$ crm_mon -1'):
                continue
            if re.match(r'^\[[^\]]+@[^\]]+\s+[^\]]+\][#$]\s*$', stripped):
                continue
            lines.append(line)

        if command_not_found:
            return {
                'cluster_configured': False,
                'crm_mon_available': False,
                'crm_mon_output_detected': bool(lines),
                'command_error_detected': False,
                'node_count_configured': None,
                'resource_instance_count_configured': None,
                'online_node_count': 0,
                'online_nodes': [],
                'offline_node_count': 0,
                'offline_nodes': [],
                'maintenance_detected': False,
                'daemon_status': {},
                'command_error': lines[0].strip() if lines else 'crm_mon command not found',
            }

        command_error_detected = False
        command_error = ''
        online_nodes = []
        offline_nodes = []
        daemon_status = {}
        node_count_configured = None
        resource_instance_count_configured = None
        maintenance_detected = False
        in_daemon_status = False

        for line in lines:
            stripped = line.strip()
            lowered_line = stripped.lower()
            maintenance_detected = maintenance_detected or 'maintenance' in lowered_line
            if not command_error_detected and (
                re.match(r'^(?:bash|sh|ksh|zsh|su|sudo):', lowered_line)
                or 'permission denied' in lowered_line
                or 'cannot execute' in lowered_line
                or 'cluster is not available' in lowered_line
                or 'connection to cluster failed' in lowered_line
            ):
                command_error_detected = True
                command_error = stripped

            match = re.match(r'^(?:\*\s*)?(\d+)\s+nodes?\s+configured$', stripped, re.IGNORECASE)
            if match:
                node_count_configured = int(match.group(1))
                continue

            match = re.match(r'^(?:\*\s*)?(\d+)\s+resource\s+instances?\s+configured$', stripped, re.IGNORECASE)
            if match:
                resource_instance_count_configured = int(match.group(1))
                continue

            if re.search(r'\bonline\s*:', lowered_line):
                match = re.search(r'\[(.*?)\]', line)
                node_text = match.group(1) if match else line.split(':', 1)[1]
                online_nodes.extend(
                    token.strip().strip(',')
                    for token in node_text.split()
                    if token.strip().strip(',')
                )

            if re.search(r'\boffline\s*:', lowered_line):
                match = re.search(r'\[(.*?)\]', line)
                node_text = match.group(1) if match else line.split(':', 1)[1]
                offline_nodes.extend(
                    token.strip().strip(',')
                    for token in node_text.split()
                    if token.strip().strip(',')
                )

            if lowered_line == 'daemon status:':
                in_daemon_status = True
                continue

            if in_daemon_status:
                if not line.startswith((' ', '\t')):
                    in_daemon_status = False
                    continue
                if ':' not in stripped:
                    continue
                name, status_text = stripped.split(':', 1)
                daemon_status[name.strip()] = status_text.strip()

        online_nodes = sorted(set(online_nodes))
        offline_nodes = sorted(set(offline_nodes))

        return {
            'cluster_configured': True,
            'crm_mon_available': True,
            'crm_mon_output_detected': bool(lines),
            'command_error_detected': command_error_detected,
            'command_error': command_error,
            'node_count_configured': node_count_configured,
            'resource_instance_count_configured': resource_instance_count_configured,
            'online_node_count': len(online_nodes),
            'online_nodes': online_nodes,
            'offline_node_count': len(offline_nodes),
            'offline_nodes': offline_nodes,
            'maintenance_detected': maintenance_detected,
            'daemon_status': daemon_status,
            'crm_mon_line_count': len(lines),
        }

    def evaluate(self, metrics, threshold):
        try:
            threshold_value = int(threshold)
        except Exception:
            threshold_value = 0

        if not metrics.get('crm_mon_available', True):
            return 'ok'
        if not metrics.get('command_result_received', True):
            return 'fail'
        if metrics.get('command_error_detected'):
            return 'fail'
        if not metrics.get('crm_mon_output_detected', False):
            return 'fail'
        if int(metrics.get('offline_node_count') or 0) > threshold_value:
            return 'fail'
        return 'ok'

    def build_result(self, metrics, threshold, status):
        offline_nodes = metrics.get('offline_nodes') or []
        online_nodes = metrics.get('online_nodes') or []
        daemon_status = metrics.get('daemon_status') or {}
        maintenance_message = ''
        if metrics.get('maintenance_detected'):
            maintenance_message = ' Maintenance 상태가 표시되어 계획 작업 여부 확인이 필요합니다.'

        daemon_text = ', '.join(
            '%s=%s' % (name, state)
            for name, state in sorted(daemon_status.items())
        ) or '수집 없음'
        online_text = ', '.join(online_nodes) or '없음'
        offline_text = ', '.join(offline_nodes) or '없음'

        result = {
            'message': '',
            'results': (
                'Online 노드: {online} / Offline 노드: {offline} / '
                'Daemon Status: {daemon}'
            ).format(
                online=online_text,
                offline=offline_text,
                daemon=daemon_text,
            ),
            'criteria': (
                '정상: Offline 노드 {threshold}개 이하 / '
                '불량: Offline 노드 {threshold}개 초과 / '
                'crm_mon 미존재: 클러스터 미구성으로 정상'
            ).format(threshold=threshold),
        }

        if not metrics.get('crm_mon_available', True):
            result['message'] = 'Cluster 데몬 상태 점검 대상이 아닙니다. crm_mon 명령이 없어 클러스터 미구성으로 판단했습니다.'
            result['results'] = 'crm_mon 명령 미존재: %s' % metrics.get('command_error', 'crm_mon command not found')
            return result

        if not metrics.get('command_result_received', True):
            result['message'] = 'Cluster 데몬 상태 점검 실패: Paramiko 명령 실행 결과가 비어 있습니다.'
            result['results'] = 'Paramiko 명령 실행 결과 없음'
            return result

        if metrics.get('command_error_detected'):
            result['message'] = 'Cluster 데몬 상태 점검 실패: crm_mon -1 명령 실행에 실패했습니다.'
            result['results'] = metrics.get('command_error') or metrics.get('command_stderr') or '명령 실행 실패'
            return result

        if not metrics.get('crm_mon_output_detected', False):
            result['message'] = 'Cluster 데몬 상태 점검 실패: crm_mon -1 출력 결과가 비어 있습니다.'
            result['results'] = 'crm_mon -1 출력 결과 없음'
            return result

        if status == 'fail':
            result['message'] = (
                'Cluster 데몬 상태 점검 불량: Offline 노드 {count}개({nodes}), 기준 {threshold}개 이하.'
            ).format(
                count=metrics.get('offline_node_count', 0),
                nodes=offline_text,
                threshold=threshold,
            )
            return result

        result['message'] = (
            'Cluster 데몬 상태 점검 정상: Online 노드 {online_count}개, Offline 노드 {offline_count}개.'
        ).format(
            online_count=metrics.get('online_node_count', 0),
            offline_count=metrics.get('offline_node_count', 0),
        ) + maintenance_message
        return result

    def run(self):
        threshold = self.get_threshold_var(
            'max_offline_node_count',
            default=0,
            value_type='int',
        )

        results = self._run_paramiko_commands(
            'crm_mon -1',
            become=True,
            profile='linux',
            timeout_sec=25,
        )
        command_result = results[-1] if results else {}
        stdout = (command_result.get('stdout') or '').strip()
        stderr = (command_result.get('stderr') or '').strip()

        output = '\n'.join(part for part in (stdout, stderr) if part).strip()
        metrics = self.parse_output(output)
        metrics['command_result_received'] = bool(results)
        if stderr:
            metrics['command_stderr'] = stderr

        status = self.evaluate(metrics, threshold)
        result = self.build_result(metrics, threshold, status)

        return self.result(
            status=status,
            message=result['message'],
            metrics=metrics,
            results=result['results'],
            criteria=result['criteria'],
        )


CHECK_CLASS = Check
