# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


CLUSTER_DAEMON_COMMAND = (
    "if(Get-Module -ListAvailable -Name FailoverClusters)"
    "{Import-Module FailoverClusters -ErrorAction SilentlyContinue; $cl='.'; "
    "try{$c=if($cl -eq '.'){Get-Cluster -ErrorAction Stop}else{Get-Cluster -Name $cl -ErrorAction Stop}; "
    "$n=Get-ClusterNode -Cluster $cl -ErrorAction Stop; $r=Get-ClusterResource -Cluster $cl -ErrorAction Stop; "
    "'==Cluster Summary=='; "
    "[pscustomobject]@{Cluster=$c.Name; NodesConfigured=$n.Count; NodesOnline=($n|Where-Object State -eq 'Up').Count; ResourceInstancesConfigured=$r.Count; ResourcesOnline=($r|Where-Object State -eq 'Online').Count}|Format-List; "
    "'==Node List=='; $n|Select-Object Name,Id,State|Format-Table -Auto; "
    "'==Full List of Resources=='; $r|Select-Object Name,State,ResourceType,OwnerGroup,OwnerNode|Format-Table -Auto; "
    "'==Fence History=='; 'N/A (no direct crm_mon-style fencing history field in WSFC PowerShell)'} "
    "catch {'Failover cluster not found/reachable. For remote WSFC, change $cl=''.'' to your cluster name.'}} "
    "else {'FailoverClusters module not installed. On Windows 11, install RSAT Failover Clustering Tools first.'}"
)


def _parse_int(value):
    return int(str(value).strip())


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
            return self.not_applicable(
                'WinRM 실행 환경을 사용할 수 없습니다.',
                raw_output=(err or '').strip(),
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
            return self.ok(
                metrics={
                    'cluster_module_installed': False,
                    'cluster_reachable': False,
                    'nodes_configured': 0,
                    'nodes_online': 0,
                    'down_node_count': 0,
                    'resource_instances_configured': 0,
                    'resources_online': 0,
                    'offline_resource_count': 0,
                    'matched_failure_keywords': [],
                },
                thresholds={
                    'max_down_node_count': max_down_node_count,
                    'max_offline_resource_count': max_offline_resource_count,
                    'failure_keywords': [],
                },
                reasons='FailoverClusters 모듈 또는 로컬 WSFC 정보가 확인되지 않았습니다.',
                message='Windows 클러스터 데몬 상태 점검이 정상 수행되었습니다.',
            )

        if 'FailoverClusters module not installed. On Windows 11, install RSAT Failover Clustering Tools first.' in text:
            return self.ok(
                metrics={
                    'cluster_module_installed': False,
                    'cluster_reachable': False,
                    'nodes_configured': 0,
                    'nodes_online': 0,
                    'down_node_count': 0,
                    'resource_instances_configured': 0,
                    'resources_online': 0,
                    'offline_resource_count': 0,
                    'matched_failure_keywords': [],
                },
                thresholds={
                    'max_down_node_count': max_down_node_count,
                    'max_offline_resource_count': max_offline_resource_count,
                    'failure_keywords': [],
                },
                reasons='FailoverClusters 모듈이 설치되어 있지 않으며, 일반적인 Windows 11 환경에서는 RSAT Failover Clustering Tools를 별도 설치해야 합니다.',
                message='Windows 클러스터 데몬 상태 점검이 정상 수행되었습니다.',
            )

        if 'Failover cluster not found/reachable.' in text:
            return self.ok(
                metrics={
                    'cluster_module_installed': True,
                    'cluster_reachable': False,
                    'nodes_configured': 0,
                    'nodes_online': 0,
                    'down_node_count': 0,
                    'resource_instances_configured': 0,
                    'resources_online': 0,
                    'offline_resource_count': 0,
                    'matched_failure_keywords': [],
                },
                thresholds={
                    'max_down_node_count': max_down_node_count,
                    'max_offline_resource_count': max_offline_resource_count,
                    'failure_keywords': [],
                },
                reasons='FailoverClusters 모듈은 있으나 로컬 또는 지정된 WSFC 클러스터에 연결되지 않았습니다.',
                message='Windows 클러스터 데몬 상태 점검이 정상 수행되었습니다.',
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

        lines = [line.rstrip() for line in text.splitlines()]
        summary = {}
        node_entries = []
        resource_entries = []
        section = None

        for raw_line in lines:
            line = raw_line.rstrip()
            stripped = line.strip()
            if not stripped:
                continue

            if stripped == '==Cluster Summary==':
                section = 'summary'
                continue
            if stripped == '==Node List==':
                section = 'nodes'
                continue
            if stripped == '==Full List of Resources==':
                section = 'resources'
                continue
            if stripped == '==Fence History==':
                section = 'fence'
                continue

            if stripped.startswith('----') or stripped.startswith('-----------'):
                continue

            if section == 'summary':
                if ':' in stripped:
                    key, value = stripped.split(':', 1)
                    summary[key.strip()] = value.strip()
                continue

            if section == 'nodes':
                if stripped.startswith('Name') and 'State' in stripped:
                    continue
                parts = [part.strip() for part in re.split(r'\s{2,}', stripped) if part.strip()]
                if len(parts) >= 3:
                    node_entries.append({
                        'name': parts[0],
                        'id': parts[1],
                        'state': parts[2],
                    })
                continue

            if section == 'resources':
                if stripped.startswith('Name') and 'OwnerNode' in stripped:
                    continue
                parts = [part.strip() for part in re.split(r'\s{2,}', stripped) if part.strip()]
                if len(parts) >= 5:
                    resource_entries.append({
                        'name': parts[0],
                        'state': parts[1],
                        'resource_type': parts[2],
                        'owner_group': parts[3],
                        'owner_node': parts[4],
                    })

        if not summary:
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
            message='Windows 클러스터 데몬 상태 점검이 정상 수행되었습니다.',
        )


CHECK_CLASS = Check
