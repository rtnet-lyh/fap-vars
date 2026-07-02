# -*- coding: utf-8 -*-
import json

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


def _humanize_threshold_key(key):
    text = str(key or '').strip()
    if not text:
        return ''
    direct = {
        'failure_keywords': '?? ???',
        'max_usr_sys_percent': '???+??? CPU ??? ?? ??',
        'min_idle_percent': 'CPU ??? ?? ??',
        'max_interrupt_percent': '???? ?? ?? ?? ??',
        'max_memory_usage_percent': '??? ??? ?? ??',
        'min_memory_free_percent': '?? ??? ?? ?? ??',
        'max_swap_usage_percent': '?? ??? ?? ??',
        'min_socket_count': '?? CPU ?? ? ?? ??',
        'min_total_core_count': '?? CPU ?? ? ?? ??',
        'min_total_logical_processor_count': '?? CPU ? ?? ??',
        'min_installed_memory_gib': '?? ??? ?? ?? ??',
        'max_usage_percent': '??? ?? ??',
        'min_available_percent': '??? ?? ??',
        'require_spare_device': '?? ??? ?? ??',
        'min_disk_count': '??? ? ?? ??',
        'min_partition_count': '??? ? ?? ??',
        'max_wait_ms': '?? ?? ?? ??(ms)',
        'max_busy_percent': 'Busy ?? ?? ??',
        'max_queue_length': '? ?? ?? ??',
        'max_iuse_percent': 'inode ?? ??? ?? ??',
        'expected_tcp_state': '?? TCP ??',
        'max_recent_error_count': '?? ?? ? ?? ??',
        'expected_service_state': '?? ??? ??',
        'expected_mount_path': '?? ??? ??',
        'expected_mode': '?? ??',
        'min_up_physical_nic_count': 'Up ?? ?? NIC ? ?? ??',
        'expected_team_count': 'NIC Team ? ?? ??',
        'max_packet_loss_percent': '?? ??? ?? ??',
        'max_average_latency_ms': '?? ???? ?? ??(ms)',
        'max_non_optimized_path_count': '??? ?? ? ?? ??',
        'max_non_online_port_count': '??? FC HBA ?? ? ?? ??',
        'max_cluster_event_count': '???? ??? ? ?? ??',
        'max_cpu_event_count': 'CPU ??? ? ?? ??',
        'max_fan_event_count': 'FAN ??? ? ?? ??',
        'max_hba_event_count': 'HBA ??? ? ?? ??',
        'max_io_event_count': 'I/O ??? ? ?? ??',
        'max_panic_like_event_count': '?? ??? ??? ? ?? ??',
        'max_memory_event_count': '??? ??? ? ?? ??',
        'max_nic_event_count': 'NIC ??? ? ?? ??',
        'max_power_event_count': '?? ??? ? ?? ??',
    }
    if text in direct:
        return direct[text]
    return text

class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'winrm'
    WINRM_SHELL = 'powershell'


    def parse_output(self, output):
        text = (output or '').strip()
        metrics = {
            "cluster_name": "",
            "nodes_configured": 0,
            "nodes_online": 0,
            "down_node_count": 0,
            "down_nodes": [],
            "resource_instances_configured": 0,
            "resources_online": 0,
            "offline_resource_count": 0,
            "offline_resources": [],
            "cluster_module_installed": True,
            "cluster_reachable": True,
            "matched_failure_keywords": [],
            "parse_state": "ok",
            "raw_text": text,
        }

        if not text:
            metrics["parse_state"] = "empty"
            return metrics

        lowered = text.lower()
        if "failoverclusters module not installed" in lowered:
            metrics["cluster_module_installed"] = False
            metrics["cluster_reachable"] = False
            metrics["parse_state"] = "module_missing"
            return metrics

        if "cannot find any service with service name 'clussvc'" in lowered:
            metrics["cluster_reachable"] = False
            metrics["parse_state"] = "service_missing"
            return metrics

        if "get-clusternode" in lowered or "get-clusterresource" in lowered or "not recognized" in lowered:
            metrics["cluster_reachable"] = False
            metrics["parse_state"] = "cluster_unreachable"
            return metrics

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
            elif section == 'resources':
                resource_count += 1
                if state.lower() == 'online':
                    resources_online += 1
                else:
                    offline_resources.append(name)

        if node_count == 0 and resource_count == 0:
            metrics["parse_state"] = "summary_missing"
            return metrics

        metrics["cluster_name"] = "WSFC"
        metrics["nodes_configured"] = node_count
        metrics["nodes_online"] = nodes_online
        metrics["down_node_count"] = len(down_nodes)
        metrics["down_nodes"] = down_nodes
        metrics["resource_instances_configured"] = resource_count
        metrics["resources_online"] = resources_online
        metrics["offline_resource_count"] = len(offline_resources)
        metrics["offline_resources"] = offline_resources
        return metrics

    def evaluate(self, metrics, max_down_node_count, max_offline_resource_count, failure_keywords):
        raw_text = metrics["raw_text"]
        matched_failure_keywords = []
        for keyword in failure_keywords:
            if keyword and keyword.lower() in raw_text.lower():
                matched_failure_keywords.append(keyword)
        metrics["matched_failure_keywords"] = matched_failure_keywords

        if metrics["parse_state"] == "service_missing":
            return "excluded"
        if metrics["parse_state"] != "ok":
            return "fail"
        if matched_failure_keywords:
            return "fail"
        if metrics["down_node_count"] > max_down_node_count:
            return "fail"
        if metrics["offline_resource_count"] > max_offline_resource_count:
            return "fail"
        return "ok"

    def build_result(self, metrics, max_down_node_count, max_offline_resource_count, failure_keywords, status):
        result = {}
        result["message"] = None
        result["results"] = (
            f"cluster={metrics['cluster_name']}, "
            f"노드 {metrics['nodes_online']}/{metrics['nodes_configured']} Online, "
            f"Down {metrics['down_node_count']}개, "
            f"리소스 {metrics['resources_online']}/{metrics['resource_instances_configured']} Online, "
            f"Offline {metrics['offline_resource_count']}개"
        )
        result["criteria"] = (
            f"정상: Down 노드 {max_down_node_count}개 이하 / "
            f"Offline 리소스 {max_offline_resource_count}개 이하 / "
            f"실패 키워드 미검출"
        )

        if metrics["parse_state"] == "module_missing":
            result["message"] = "FailoverClusters 모듈 미설치"
        elif metrics["parse_state"] == "service_missing":
            result["message"] = "WSFC 미구성 또는 서비스 없음"
        elif metrics["parse_state"] == "cluster_unreachable":
            result["message"] = "WSFC 클러스터 연결 불가"
        elif metrics["parse_state"] == "empty":
            result["message"] = "클러스터 데몬 상태 정보 없음"
        elif metrics["parse_state"] in ("summary_missing",):
            result["message"] = "클러스터 상태 파싱 실패"
        elif metrics["matched_failure_keywords"]:
            result["message"] = "클러스터 데몬 실패 키워드 감지"
        elif metrics["down_node_count"] > max_down_node_count:
            result["message"] = "클러스터 노드 상태 이상 감지"
        elif metrics["offline_resource_count"] > max_offline_resource_count:
            result["message"] = "클러스터 리소스 상태 이상 감지"
        elif status == "ok":
            result["message"] = "Windows 클러스터 데몬 상태 정상"
        else:
            result["message"] = "Windows 클러스터 데몬 상태 불량"

        if metrics["matched_failure_keywords"]:
            result["results"] += f", 실패 키워드={','.join(metrics['matched_failure_keywords'])}"
        if metrics["down_nodes"]:
            result["results"] += f", Down 노드={','.join(metrics['down_nodes'])}"
        if metrics["offline_resources"]:
            result["results"] += f", Offline 리소스={','.join(metrics['offline_resources'])}"
        if failure_keywords:
            result["criteria"] += f" / failure_keywords={','.join(failure_keywords)}"

        return result

    def run(self):
        max_down_node_count = self.get_threshold_var("max_down_node_count", default=0, value_type='int')
        max_offline_resource_count = self.get_threshold_var("max_offline_resource_count", default=0, value_type='int')
        failure_keywords_raw = self.get_threshold_var("failure_keywords", default="", value_type='str')
        failure_keywords = [keyword.strip() for keyword in failure_keywords_raw.split(",") if keyword.strip()]

        rc, out, err = self._run_ps(_prepare_windows_command(CLUSTER_DAEMON_COMMAND))
        output = out if (out or '').strip() else err

        metrics = self.parse_output(output)
        status = self.evaluate(
            metrics,
            max_down_node_count,
            max_offline_resource_count,
            failure_keywords,
        )
        result = self.build_result(
            metrics,
            max_down_node_count,
            max_offline_resource_count,
            failure_keywords,
            status,
        )

        return self.result(
            status=status,
            message=result["message"],
            metrics=metrics,
            results=result["results"],
            criteria=result["criteria"],
        )


CHECK_CLASS = Check
