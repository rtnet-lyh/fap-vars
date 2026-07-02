# -*- coding: utf-8 -*-

from items.common._base import BaseCheck


CLUSTER_DAEMON_COMMAND = "powershell -Command \"try { Get-Service clussvc -ErrorAction Stop | Out-Null; Write-Host '[Node Status]'; Get-ClusterNode | ForEach-Object { '{0} : {1}' -f $_.Name, $_.State }; Write-Host '---'; Write-Host '[Service Status]'; Get-ClusterResource | ForEach-Object { '{0} : {1}' -f $_.Name, $_.State } } catch { $_ | Out-String }\""


def _prepare_windows_command(command):
    text = (command or '').strip()
    prefixes = (
        'powershell.exe -NoProfile -Command ',
        'powershell -Command ',
    )
    for prefix in prefixes:
        if text.startswith(prefix):
            payload = text[len(prefix):].strip()
            if len(payload) >= 2 and payload[0] == payload[-1] and payload[0] in ('"', "'"):
                payload = payload[1:-1]
            payload = payload.replace('\\"', '"')
            payload = payload.replace("\\'", "'")
            return payload
    return text


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'winrm'
    WINRM_SHELL = 'powershell'

    def parse_output(self, legacy_result):
        metrics = dict(legacy_result.get("metrics") or {})
        metrics["_legacy_result"] = legacy_result
        return metrics

    def evaluate(self, metrics):
        legacy_result = metrics.get("_legacy_result", {})
        status = str(legacy_result.get("status", "fail")).strip().lower()
        if status in ("ok", "warn", "fail", "excluded"):
            return status
        return "fail"

    def build_result(self, metrics, status):
        legacy_result = metrics.get("_legacy_result", {})
        final_metrics = dict(metrics)
        final_metrics.pop("_legacy_result", None)

        thresholds = legacy_result.get("thresholds", {})
        results_text = legacy_result.get("results")
        if not results_text:
            results_text = legacy_result.get("reasons", "")
        if not results_text:
            message_text = str(legacy_result.get("message") or "").strip()
            if "현재 상태:" in message_text:
                results_text = message_text.split("현재 상태:", 1)[1].strip()
            else:
                results_text = message_text
        if not results_text and final_metrics:
            parts = []
            for key, value in final_metrics.items():
                if value in (None, "", [], {}):
                    continue
                parts.append(f"{key}={value}")
            results_text = ", ".join(parts)

        criteria_text = legacy_result.get("criteria")
        if not criteria_text:
            if isinstance(thresholds, dict) and thresholds:
                criteria_text = ", ".join(
                    f"{key}={value}" for key, value in thresholds.items()
                )
            else:
                criteria_text = ""

        return {
            "message": legacy_result.get("message"),
            "results": results_text,
            "criteria": criteria_text,
            "error": legacy_result.get("error"),
            "raw_output": legacy_result.get("raw_output"),
            "stdout": legacy_result.get("stdout"),
            "stderr": legacy_result.get("stderr"),
            "metrics": final_metrics,
        }

    def run(self):
        legacy_result = self.execute_check()
        metrics = self.parse_output(legacy_result)
        status = self.evaluate(metrics)
        result = self.build_result(metrics, status)

        thresholds = result["criteria"] if isinstance(result["criteria"], dict) else {"criteria": result["criteria"]}

        if status == "ok":
            return self.ok(
                metrics=result["metrics"],
                thresholds=thresholds,
                reasons=result["results"],
                message=result["message"],
                results=result["results"],
                criteria=result["criteria"],
            )
        if status == "warn":
            return self.warn(
                metrics=result["metrics"],
                thresholds=thresholds,
                reasons=result["results"],
                message=result["message"],
                results=result["results"],
                criteria=result["criteria"],
            )
        if status == "excluded":
            return self.not_applicable(
                message=result["message"],
                raw_output=result.get("raw_output") or result["results"],
            )
        return self.fail(
            error=result.get("error") or result["message"],
            message=result["message"],
            metrics=result["metrics"],
            thresholds=thresholds,
            reasons=result["results"],
            raw_output=result.get("raw_output"),
            stdout=result.get("stdout"),
            stderr=result.get("stderr"),
            results=result["results"],
            criteria=result["criteria"],
        )

    def execute_check(self):
        max_down_node_count = self.get_threshold_var('max_down_node_count', default=0, value_type='int')
        max_offline_resource_count = self.get_threshold_var('max_offline_resource_count', default=0, value_type='int')
        failure_keywords_raw = self.get_threshold_var('failure_keywords', default='', value_type='str')

        rc, out, err = self._run_ps(_prepare_windows_command(CLUSTER_DAEMON_COMMAND))
        if self._is_connection_error(rc, err):
            return self.fail('호스트 연결 실패', message=(err or 'WinRM 연결 확인에 실패했습니다.').strip(), stderr=(err or '').strip())
        if self._is_not_applicable(rc, err):
            return self.fail('WinRM 실행 환경을 사용할 수 없습니다.', message='Windows 클러스터 데몬 상태 점검을 수행할 수 없습니다.', stdout=(out or '').strip(), stderr=(err or '').strip())

        text = (out if (out or '').strip() else err or '').strip()
        stderr_text = (err or '').strip()

        if rc != 0 and not text:
            return self.fail('점검 명령 실행 실패', message='Windows 클러스터 데몬 상태 점검 명령 실행에 실패했습니다.', stdout=(out or '').strip(), stderr=stderr_text)

        if not text:
            return self.fail('클러스터 데몬 상태 정보 없음', message='클러스터 데몬 상태 결과가 비어 있습니다.', stdout='', stderr=stderr_text)

        lowered = text.lower()
        if "cannot find any service with service name 'clussvc'" in lowered:
            return self.not_applicable(message='WSFC 미구성 또는 서비스 없음', raw_output=text)
        if "failoverclusters module not installed" in lowered:
            return self.fail('FailoverClusters 모듈 미설치', message='FailoverClusters 모듈이 설치되어 있지 않습니다.', stdout=text, stderr=stderr_text)
        if "get-clusternode" in lowered or "get-clusterresource" in lowered or "not recognized" in lowered:
            return self.fail('WSFC 클러스터 연결 불가', message='WSFC 클러스터 상태 조회 명령을 실행할 수 없습니다.', stdout=text, stderr=stderr_text)

        failure_keywords = [keyword.strip() for keyword in failure_keywords_raw.split(',') if keyword.strip()]
        matched_failure_keywords = [keyword for keyword in failure_keywords if keyword.lower() in text.lower()]
        if matched_failure_keywords:
            return self.fail('클러스터 데몬 실패 키워드 감지', message='클러스터 데몬 상태 결과에서 실패 키워드가 확인되었습니다.', stdout=text, stderr=stderr_text)

        section = None
        down_nodes = []
        offline_resources = []
        node_count = 0
        resource_count = 0
        nodes_online = 0
        resources_online = 0

        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if line == '[Node Status]':
                section = 'nodes'
                continue
            if line == '[Service Status]':
                section = 'resources'
                continue
            if line == '---':
                continue
            if ' : ' not in line:
                continue

            name, state = [part.strip() for part in line.split(' : ', 1)]

            if section == 'nodes':
                node_count += 1
                if state.lower() == 'up':
                    nodes_online += 1
                else:
                    down_nodes.append(name)

            if section == 'resources':
                resource_count += 1
                if state.lower() == 'online':
                    resources_online += 1
                else:
                    offline_resources.append(name)

        if node_count == 0 and resource_count == 0:
            return self.fail('클러스터 상태 파싱 실패', message='클러스터 노드 또는 리소스 상태를 해석하지 못했습니다.', stdout=text, stderr=stderr_text)

        down_node_count = len(down_nodes)
        offline_resource_count = len(offline_resources)

        if down_node_count > max_down_node_count:
            return self.fail('클러스터 노드 상태 이상 감지', message=f'Windows 클러스터 데몬 상태 점검에 실패했습니다. 현재 상태: Down 노드 {down_node_count}개 (기준 {max_down_node_count}개 이하).', stdout=text, stderr=stderr_text)

        if offline_resource_count > max_offline_resource_count:
            return self.fail('클러스터 리소스 상태 이상 감지', message=f'Windows 클러스터 데몬 상태 점검에 실패했습니다. 현재 상태: Offline 리소스 {offline_resource_count}개 (기준 {max_offline_resource_count}개 이하).', stdout=text, stderr=stderr_text)

        return self.ok(
            metrics={
                'cluster_name': 'WSFC',
                'nodes_configured': node_count,
                'nodes_online': nodes_online,
                'down_node_count': down_node_count,
                'down_nodes': down_nodes,
                'resource_instances_configured': resource_count,
                'resources_online': resources_online,
                'offline_resource_count': offline_resource_count,
                'offline_resources': offline_resources,
                'matched_failure_keywords': matched_failure_keywords,
            },
            thresholds={
                '최대 Down 노드 수': max_down_node_count,
                '최대 Offline 리소스 수': max_offline_resource_count,
                '실패 키워드': failure_keywords,
            },
            reasons=(
                f'노드 {nodes_online}/{node_count} Online, Down {down_node_count}개 '
                f'(기준 {max_down_node_count}개 이하), '
                f'리소스 {resources_online}/{resource_count} Online, Offline {offline_resource_count}개 '
                f'(기준 {max_offline_resource_count}개 이하).'
            ),
            message='Windows 클러스터 데몬 상태가 기준 범위 내입니다.',
        )


CHECK_CLASS = Check