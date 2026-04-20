# -*- coding: utf-8 -*-

import json

from .common._base import BaseCheck


CLUSTER_DAEMON_COMMAND = (
    "$OutputEncoding = [System.Text.UTF8Encoding]::new($false); "
    "[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); "
    "if(Get-Module -ListAvailable -Name FailoverClusters)"
    "{Import-Module FailoverClusters -ErrorAction SilentlyContinue; $cl='.'; "
    "try{$c=if($cl -eq '.'){Get-Cluster -ErrorAction Stop}else{Get-Cluster -Name $cl -ErrorAction Stop}; "
    "$n=Get-ClusterNode -Cluster $cl -ErrorAction Stop; $r=Get-ClusterResource -Cluster $cl -ErrorAction Stop; "
    "$result=[ordered]@{"
    "Summary=[ordered]@{Cluster=$c.Name; NodesConfigured=$n.Count; NodesOnline=($n|Where-Object State -eq 'Up').Count; ResourceInstancesConfigured=$r.Count; ResourcesOnline=($r|Where-Object State -eq 'Online').Count}; "
    "Nodes=@($n|Select-Object Name,Id,State); "
    "Resources=@($r|Select-Object Name,State,ResourceType,OwnerGroup,OwnerNode); "
    "FenceHistory='N/A (no direct crm_mon-style fencing history field in WSFC PowerShell)'"
    "}; "
    "$result|ConvertTo-Json -Depth 4} "
    "catch {'Failover cluster not found/reachable. For remote WSFC, change $cl=''.'' to your cluster name.'}} "
    "else {'FailoverClusters module not installed. On Windows 11, install RSAT Failover Clustering Tools first.'}"
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
        max_down_node_count = self.get_threshold_var('max_down_node_count', default=0, value_type='int')
        max_offline_resource_count = self.get_threshold_var('max_offline_resource_count', default=0, value_type='int')
        failure_keywords_raw = self.get_threshold_var('failure_keywords', default='', value_type='str')

        rc, out, err = self._run_ps(CLUSTER_DAEMON_COMMAND)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'WinRM 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if self._is_not_applicable(rc, err):
            return self.fail(
                'WinRM 실행 환경을 사용할 수 없습니다.',
                message='Windows 클러스터 데몬 상태 점검을 수행할 수 없습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='Windows 클러스터 데몬 상태 점검 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        text = (out or '').strip()
        if not text:
            return self.fail(
                '클러스터 데몬 상태 정보 없음',
                message=(
                    'Windows 클러스터 데몬 상태 점검에 실패했습니다. '
                    '현재 상태: FailoverClusters 모듈 또는 로컬 WSFC 정보를 확인할 수 없어 '
                    '노드 0/0, 온라인 리소스 0/0으로 집계했습니다.'
                ),
                stdout='',
                stderr=(err or '').strip(),
            )

        if 'FailoverClusters module not installed. On Windows 11, install RSAT Failover Clustering Tools first.' in text:
            return self.fail(
                'FailoverClusters 모듈 미설치',
                message=(
                    'Windows 클러스터 데몬 상태 점검에 실패했습니다. '
                    '현재 상태: FailoverClusters 모듈이 설치되어 있지 않아 '
                    '로컬 WSFC 연결이 없으며 노드 0/0, 온라인 리소스 0/0으로 집계했습니다.'
                ),
                stdout=text,
                stderr=(err or '').strip(),
            )

        if 'Failover cluster not found/reachable.' in text:
            return self.fail(
                'WSFC 클러스터 연결 불가',
                message=(
                    'Windows 클러스터 데몬 상태 점검에 실패했습니다. '
                    '현재 상태: FailoverClusters 모듈은 확인됐지만 로컬 또는 지정된 WSFC 클러스터에 연결되지 않아 '
                    '노드 0/0, 온라인 리소스 0/0으로 집계했습니다.'
                ),
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
                '클러스터 데몬 실패 키워드 감지',
                message='클러스터 데몬 상태 결과에서 실패 키워드가 확인되었습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return self.fail(
                '클러스터 요약 파싱 실패',
                message='클러스터 상태 JSON을 해석하지 못했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        summary = parsed.get('Summary', {}) if isinstance(parsed, dict) else {}
        node_entries = []
        resource_entries = []

        for entry in _as_list(parsed.get('Nodes', [])) if isinstance(parsed, dict) else []:
            if isinstance(entry, dict):
                node_entries.append({
                    'name': str(entry.get('Name', '')).strip(),
                    'id': str(entry.get('Id', '')).strip(),
                    'state': str(entry.get('State', '')).strip(),
                })

        for entry in _as_list(parsed.get('Resources', [])) if isinstance(parsed, dict) else []:
            if isinstance(entry, dict):
                resource_entries.append({
                    'name': str(entry.get('Name', '')).strip(),
                    'state': str(entry.get('State', '')).strip(),
                    'resource_type': str(entry.get('ResourceType', '')).strip(),
                    'owner_group': str(entry.get('OwnerGroup', '')).strip(),
                    'owner_node': str(entry.get('OwnerNode', '')).strip(),
                })

        if not isinstance(summary, dict) or not summary:
            return self.fail(
                '클러스터 요약 파싱 실패',
                message='클러스터 요약 정보를 해석하지 못했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        try:
            nodes_configured = _parse_int(summary.get('NodesConfigured', '0'))
            nodes_online = _parse_int(summary.get('NodesOnline', '0'))
            resource_instances_configured = _parse_int(summary.get('ResourceInstancesConfigured', '0'))
            resources_online = _parse_int(summary.get('ResourcesOnline', '0'))
        except ValueError:
            return self.fail(
                '클러스터 요약 파싱 실패',
                message='노드 또는 리소스 집계 값을 해석하지 못했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        down_nodes = [
            entry['name']
            for entry in node_entries
            if entry['state'].lower() != 'up'
        ]
        offline_resources = [
            entry['name']
            for entry in resource_entries
            if entry['state'].lower() != 'online'
        ]

        if len(down_nodes) > max_down_node_count:
            return self.fail(
                '클러스터 노드 상태 이상 감지',
                message='Down 또는 비정상 상태의 클러스터 노드가 기준치를 초과했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        if len(offline_resources) > max_offline_resource_count:
            return self.fail(
                '클러스터 리소스 상태 이상 감지',
                message='Offline 또는 비정상 상태의 클러스터 리소스가 기준치를 초과했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        reasons = '모든 클러스터 노드와 주요 리소스가 기준 범위 내에서 정상 상태입니다.'
        if not node_entries and not resource_entries:
            reasons = '클러스터 요약 정보는 확인되었으나 상세 노드/리소스 목록은 비어 있습니다.'

        return self.ok(
            metrics={
                'cluster_module_installed': True,
                'cluster_reachable': True,
                'cluster_name': summary.get('Cluster', ''),
                'nodes_configured': nodes_configured,
                'nodes_online': nodes_online,
                'down_node_count': len(down_nodes),
                'down_nodes': down_nodes,
                'resource_instances_configured': resource_instances_configured,
                'resources_online': resources_online,
                'offline_resource_count': len(offline_resources),
                'offline_resources': offline_resources,
                'matched_failure_keywords': matched_failure_keywords,
            },
            thresholds={
                'max_down_node_count': max_down_node_count,
                'max_offline_resource_count': max_offline_resource_count,
                'failure_keywords': failure_keywords,
            },
            reasons=reasons,
            message=(
                f'Windows 클러스터 데몬 상태 점검이 정상입니다. 현재 상태: '
                f'cluster={summary.get("Cluster", "")}, 노드 {nodes_online}/{nodes_configured} Online '
                f'(Down {len(down_nodes)}개, 기준 {max_down_node_count}개 이하), '
                f'리소스 {resources_online}/{resource_instances_configured} Online '
                f'(Offline {len(offline_resources)}개, 기준 {max_offline_resource_count}개 이하).'
            ),
        )


CHECK_CLASS = Check
