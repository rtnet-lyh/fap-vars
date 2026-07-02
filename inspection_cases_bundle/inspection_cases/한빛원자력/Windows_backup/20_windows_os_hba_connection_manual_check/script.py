# -*- coding: utf-8 -*-

import json

from items.common._base import BaseCheck


OS_HBA_LINK_STATUS_COMMAND = "powershell.exe -NoProfile -Command \"$cmd = Get-Command Get-InitiatorPort -ErrorAction SilentlyContinue; if (-not $cmd) { 'NOT_APPLICABLE=Get-InitiatorPort unavailable'; exit 0 }; $ports = Get-InitiatorPort; if (-not $ports) { 'NOT_APPLICABLE=No initiator port'; exit 0 }; foreach ($p in $ports) {\n  'NodeAddress=' + $p.NodeAddress;\n  'PortAddress=' + $p.PortAddress;\n  'ConnectionType=' + $p.ConnectionType;\n  'PortState=' + $p.PortState;\n  ''\n}\"\n"


def _as_list(value):
    if isinstance(value, list):
        return value
    if value in (None, ''):
        return []
    return [value]



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
            results_text = str(legacy_result.get("message") or "").strip()
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
                    f"{_humanize_threshold_key(key)}={value}" for key, value in thresholds.items()
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
        max_non_online_port_count = self.get_threshold_var('max_non_online_port_count', default=0, value_type='int')
        failure_keywords_raw = self.get_threshold_var('failure_keywords', default='', value_type='str')

        rc, out, err = self._run_ps(_prepare_windows_command(OS_HBA_LINK_STATUS_COMMAND))
        if self._is_connection_error(rc, err):
            return self.fail('호스트 연결 실패', message=(err or 'WinRM 연결 확인에 실패했습니다.').strip(), stderr=(err or '').strip())

        text = (out or '').strip()
        stderr_text = (err or '').strip()
        if self._is_not_applicable(rc, err) or text.startswith('NOT_APPLICABLE='):
            return self.not_applicable(message='FC HBA 또는 initiator port가 없어 점검에서 제외합니다.', raw_output=text or stderr_text)
        if rc != 0:
            lowered = f'{text}\n{stderr_text}'.lower()
            if 'not supported' in lowered or 'fc hba wmi class not found' in lowered:
                return self.not_applicable(message='FC HBA WMI 클래스가 없거나 대상 서버에서 지원되지 않아 점검에서 제외합니다.', raw_output=text or stderr_text)
            return self.fail('점검 명령 실행 실패', message='Windows FC HBA 링크 상태 점검 명령 실행에 실패했습니다.', stdout=text, stderr=stderr_text)
        if not text or text == 'FC HBA WMI class not found':
            return self.not_applicable(message='FC HBA 포트 정보를 확인할 수 없어 점검에서 제외합니다.', raw_output=text)

        failure_keywords = [keyword.strip() for keyword in failure_keywords_raw.split(',') if keyword.strip()]
        matched_failure_keywords = [keyword for keyword in failure_keywords if keyword.lower() in text.lower()]
        if matched_failure_keywords:
            return self.fail('FC HBA 실패 키워드 감지', message='FC HBA 링크 상태 결과에서 실패 키워드가 확인되었습니다.', stdout=text, stderr=stderr_text)

        entries = []
        current = {}
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                if current:
                    entries.append(current)
                    current = {}
                continue
            if '=' not in line:
                continue
            key, value = line.split('=', 1)
            current[key.strip()] = value.strip()
        if current:
            entries.append(current)

        if not entries:
            return self.fail('FC HBA 링크 상태 파싱 실패', message='FC HBA 포트 상태 결과를 해석하지 못했습니다.', stdout=text, stderr=stderr_text)

        normalized = []
        for entry in entries:
            normalized.append({
                'fc_portname': entry.get('PortAddress', ''),
                'fc_node_name': entry.get('NodeAddress', ''),
                'fc_state': entry.get('PortState', ''),
                'fc_speed': entry.get('ConnectionType', ''),
            })

        non_online_entries = [entry for entry in normalized if entry['fc_state'].lower() not in ('online', 'active', 'up')]
        if len(non_online_entries) > max_non_online_port_count:
            return self.fail('FC HBA 포트 상태 이상 감지', message='Online이 아닌 FC HBA 포트가 기준치를 초과했습니다.', stdout=text, stderr=stderr_text)

        return self.ok(
            metrics={
                'port_count': len(normalized),
                'non_online_port_count': len(non_online_entries),
                'ports': normalized,
                'matched_failure_keywords': matched_failure_keywords,
            },
            thresholds={
                'max_non_online_port_count': max_non_online_port_count,
                'failure_keywords': failure_keywords,
            },
            reasons=f'Windows FC HBA 링크 상태 점검이 정상입니다. 현재 상태: 포트 {len(normalized)}개, 비정상 포트 {len(non_online_entries)}개 (기준 {max_non_online_port_count}개 이하).',
            message='모든 FC HBA 포트가 기준 범위 내에서 온라인 상태입니다.',
        )


CHECK_CLASS = Check
