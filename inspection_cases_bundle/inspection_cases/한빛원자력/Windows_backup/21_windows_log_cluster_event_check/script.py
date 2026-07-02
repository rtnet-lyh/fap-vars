# -*- coding: utf-8 -*-

import json

from items.common._base import BaseCheck


LOG_CLUSTER_COMMAND = (
    "$OutputEncoding = [System.Text.UTF8Encoding]::new($false); "
    "[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); "
    "if(Get-WinEvent -ListLog 'Microsoft-Windows-FailoverClustering/Operational' -ErrorAction SilentlyContinue)"
    "{Get-WinEvent -FilterHashtable @{LogName='Microsoft-Windows-FailoverClustering/Operational'; StartTime=(Get-Date).AddDays(-30)} "
    "-ErrorAction SilentlyContinue | Where-Object { $_.Message -match '(?i)cluster|resource status|unknown|offline|online|error' } | "
    "Select-Object -First 100 TimeCreated,Id,LevelDisplayName,@{N='Message';E={($_.Message -replace '\\r?\\n',' ')}} | ConvertTo-Json -Depth 4}"
    "else{'Failover Clustering log not present on this PC (Windows 11 is typically not a local WSFC node).'}"
)


def _parse_int(value):
    return int(str(value).strip())


def _as_list(value):
    if isinstance(value, list):
        return value
    if value in (None, ''):
        return []
    return [value]



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
        max_cluster_event_count = self.get_threshold_var('max_cluster_event_count', default=0, value_type='int')
        failure_keywords_raw = self.get_threshold_var('failure_keywords', default='', value_type='str')

        rc, out, err = self._run_ps(LOG_CLUSTER_COMMAND)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'WinRM 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if self._is_not_applicable(rc, err):
            return self.fail(
                'WinRM 실행 환경을 사용할 수 없습니다.',
                message='Windows 클러스터 로그 점검을 수행할 수 없습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='Windows 클러스터 로그 점검 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        text = (out or '').strip()
        if not text:
            return self.fail(
                '클러스터 로그 정보 없음',
                message=(
                    'Windows 클러스터 로그 점검에 실패했습니다. '
                    '현재 상태: Failover Clustering 로그 채널이 없거나 최근 30일 내 관련 이벤트를 확인할 수 없어 '
                    '이벤트 0건으로 집계했습니다.'
                ),
                stdout='',
                stderr=(err or '').strip(),
            )

        if 'Failover Clustering log not present on this PC (Windows 11 is typically not a local WSFC node).' in text:
            return self.fail(
                'Failover Clustering 로그 채널 미존재',
                message=(
                    'Windows 클러스터 로그 점검에 실패했습니다. '
                    '현재 상태: 로컬 PC에 Failover Clustering 로그 채널이 없어 이벤트 0건으로 집계했습니다.'
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
                '클러스터 로그 실패 키워드 감지',
                message='클러스터 로그 결과에서 실패 키워드가 확인되었습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        try:
            raw_entries = json.loads(text)
        except json.JSONDecodeError:
            return self.fail(
                '클러스터 로그 파싱 실패',
                message='Failover Clustering 이벤트 JSON을 해석하지 못했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        entries = []
        for entry in _as_list(raw_entries):
            if not isinstance(entry, dict):
                continue
            event_id = entry.get('Id', '')
            entries.append({
                'time_created': str(entry.get('TimeCreated', '')).strip(),
                'event_id': _parse_int(event_id) if str(event_id).strip() else 0,
                'level': str(entry.get('LevelDisplayName', '')).strip(),
                'message': str(entry.get('Message', '')).strip(),
            })

        if not entries:
            return self.fail(
                '클러스터 로그 파싱 실패',
                message='Failover Clustering 이벤트 항목을 해석하지 못했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        offline_entries = [
            entry for entry in entries
            if 'offline' in entry['message'].lower()
        ]
        online_entries = [
            entry for entry in entries
            if 'online' in entry['message'].lower()
        ]
        unknown_or_error_entries = [
            entry for entry in entries
            if 'unknown' in entry['message'].lower()
            or 'error' in entry['message'].lower()
            or entry['level'].lower() in ('critical', 'error', '오류')
        ]
        repeated_event_ids = {}
        for entry in entries:
            key = str(entry['event_id'])
            repeated_event_ids[key] = repeated_event_ids.get(key, 0) + 1
        repeated_events = [
            f"{key}({count})"
            for key, count in repeated_event_ids.items()
            if count > 1
        ]
        latest_entry = entries[0]

        if len(entries) > max_cluster_event_count:
            return self.fail(
                '클러스터 상태 이벤트 감지',
                message='최근 30일 내 클러스터 자원 또는 노드 상태 변경 이벤트가 기준치를 초과했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        return self.ok(
            metrics={
                'cluster_log_present': True,
                'cluster_event_count': len(entries),
                'offline_event_count': len(offline_entries),
                'unknown_or_error_event_count': len(unknown_or_error_entries),
                'online_event_count': len(online_entries),
                'latest_event_time': latest_entry['time_created'],
                'latest_event_id': latest_entry['event_id'],
                'repeated_events': repeated_events,
                'matched_failure_keywords': matched_failure_keywords,
            },
            thresholds={
                'max_cluster_event_count': max_cluster_event_count,
                'failure_keywords': failure_keywords,
            },
            reasons=(
                f'Windows 클러스터 로그 점검이 정상입니다. 현재 상태: '
                f'이벤트 {len(entries)}건 (기준 {max_cluster_event_count}건 이하), '
                f'Offline {len(offline_entries)}건, Unknown/Error {len(unknown_or_error_entries)}건, '
                f'Online {len(online_entries)}건, 최신 이벤트 ID {latest_entry["event_id"]}.'
            ),
            message='최근 30일 내 클러스터 자원 또는 노드 상태 변경 이벤트 수가 기준 범위 내입니다.',
        )


CHECK_CLASS = Check
