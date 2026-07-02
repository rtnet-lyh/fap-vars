# -*- coding: utf-8 -*-

import re

from items.common._base import BaseCheck


CHECK_COMMAND = "type crm_mon >/dev/null 2>&1 || echo 'crm_mon unavailable'; type crm_mon >/dev/null 2>&1 && crm_mon -1; true"
# ---------------------------------------------------------------------
# threshold 변수 가이드
# cluster_required = False
# cluster_node_status = Online
# cluster_resource_status = True
# cluster_failed_resource = 0
# ---------------------------------------------------------------------

class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'


    def parse_output(self, output):
        text = output or ''
        if 'crm_mon unavailable' in text.lower() or not text.strip():
            return {'not_applicable': True, 'reason': 'crm_mon 실행 결과가 없거나 클러스터 출력이 비어 있어 점검 대상에서 제외합니다.'}
        online_nodes = re.findall(r'Online:\s*\[([^\]]*)\]', text, re.I)
        offline_nodes = re.findall(r'OFFLINE:\s*\[([^\]]*)\]', text, re.I)
        failed = len(re.findall(r'Failed Actions|FAILED|fail(ed)? resource', text, re.I))
        return {'online_node_groups': online_nodes, 'offline_node_groups': offline_nodes, 'failed_resource_count': failed}

    def evaluate(self, metrics, cluster_required, cluster_node_status, cluster_resource_status, cluster_failed_resource):
        if metrics.get('not_applicable'):
            return 'fail' if cluster_required else 'excluded'
        if metrics.get('failure_type'):
            return 'fail'
        if metrics['offline_node_groups']:
            return 'fail'
        if metrics['failed_resource_count'] > cluster_failed_resource:
            return 'fail'
        return 'ok'

    def build_result(self, metrics, cluster_required, cluster_node_status, cluster_resource_status, cluster_failed_resource, status):
        criteria = f"""오프라인 노드가 없고 실패 리소스 수 <= {cluster_failed_resource}
                클러스터 필수 기준이 false이면 클러스터 미구성은 제외"""
        if metrics.get('not_applicable'):
            return {'message': '클러스터 데몬 점검 대상이 아닙니다.', 'results': metrics.get('reason', ''), 'criteria': criteria}
        results = '온라인 노드 그룹 수=%d, 오프라인 노드 그룹 수=%d, 실패 리소스 수=%d' % (len(metrics.get('online_node_groups', [])), len(metrics.get('offline_node_groups', [])), metrics.get('failed_resource_count', 0))
        message = '클러스터 데몬 점검 양호' if status == 'ok' else '클러스터 데몬 상태가 기준을 만족하지 않습니다.'
        return {'message': message, 'results': results, 'criteria': criteria}

    def run(self):
        cluster_required = self.get_threshold_var('cluster_required', default=False, value_type='bool')
        cluster_node_status = self.get_threshold_var('cluster_node_status', default='Online', value_type='str')
        cluster_resource_status = self.get_threshold_var('cluster_resource_status', default='Started', value_type='str')
        cluster_failed_resource = self.get_threshold_var('cluster_failed_resource', default=0, value_type='int')

        rc, output, error = self._ssh(CHECK_COMMAND)

        if rc != 0:
            metrics = {
                'failure_type': 'command_failure',
                'rc': rc,
                'reason': (error or output or '명령 실행에 실패했습니다.').strip(),
            }
        else:
            metrics = self.parse_output(output)

        status = self.evaluate(metrics, cluster_required, cluster_node_status, cluster_resource_status, cluster_failed_resource)
        result = self.build_result(metrics, cluster_required, cluster_node_status, cluster_resource_status, cluster_failed_resource, status)

        return self.result(
            status=status,
            message=result['message'],
            metrics=metrics,
            results=result['results'],
            criteria=result['criteria'],
        )


CHECK_CLASS = Check