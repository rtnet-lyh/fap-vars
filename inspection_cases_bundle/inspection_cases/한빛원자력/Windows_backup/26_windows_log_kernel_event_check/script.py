# -*- coding: utf-8 -*-

import json

from items.common._base import BaseCheck


LOG_KERNEL_COMMAND = (
    "$OutputEncoding = [System.Text.UTF8Encoding]::new($false); "
    "[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); "
    "$events=Get-WinEvent -FilterHashtable @{LogName=@('System','Application'); StartTime=(Get-Date).AddDays(-30)} -ErrorAction SilentlyContinue | "
    "Where-Object { "
    "($_.ProviderName -eq 'Microsoft-Windows-Kernel-Power' -and $_.Id -eq 41) -or "
    "($_.ProviderName -eq 'EventLog' -and $_.Id -eq 6008) -or "
    "($_.ProviderName -match 'BugCheck|Microsoft-Windows-WER-SystemErrorReporting|Windows Error Reporting' -and "
    " $_.Message -match '(?i)bugcheck|blue ?screen|livekernelevent|kernel panic|system error') -or "
    "($_.Message -match '(?i)bugcheck|blue ?screen|livekernelevent|kernel panic') "
    "} | "
    "Sort-Object TimeCreated -Descending | "
    "Select-Object -First 100 @{N='TimeCreated';E={$_.TimeCreated.ToString('yyyy-MM-dd HH:mm:ss')}},LogName,ProviderName,Id,LevelDisplayName,@{N='Message';E={($_.Message -replace '\\r?\\n',' ')}}; "
    "if($events){$events | ConvertTo-Json -Depth 4 -Compress}else{'[]'}"
)


def _normalize_entries(raw_text):
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError:
        return None

    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        return None

    entries = []
    for item in data:
        if not isinstance(item, dict):
            continue
        entries.append({
            'time_created': str(item.get('TimeCreated', '')).strip(),
            'log_name': str(item.get('LogName', '')).strip(),
            'provider_name': str(item.get('ProviderName', '')).strip(),
            'event_id': int(item.get('Id', 0) or 0),
            'level': str(item.get('LevelDisplayName', '')).strip(),
            'message': str(item.get('Message', '')).strip(),
        })
    return entries


def _recommendations(entries, bugcheck_entries, kernel_power_41_entries, live_kernel_entries, unexpected_shutdown_entries):
    recommendations = []

    if bugcheck_entries or live_kernel_entries:
        recommendations.append('BugCheck/LiveKernelEvent가 확인되어 메모리 덤프(MEMORY.DMP 또는 Minidump) 분석이 필요합니다.')
    if kernel_power_41_entries or unexpected_shutdown_entries:
        recommendations.append('비정상 재부팅 흔적이 있어 재부팅 이후 서비스/클러스터/애플리케이션 상태 점검이 필요합니다.')
    if live_kernel_entries:
        recommendations.append('LiveKernelEvent는 드라이버 또는 하드웨어 계층 이슈 가능성이 있어 장치 드라이버와 하드웨어 상태 점검이 필요합니다.')
    if any('hardware' in entry['message'].lower() for entry in entries):
        recommendations.append('이벤트 메시지에 하드웨어 관련 단서가 있어 모델 및 펌웨어 상태를 추가 확인해야 합니다.')
    if bugcheck_entries:
        recommendations.append('이벤트 로그만으로 콜 트레이스는 확인되지 않으므로 WinDbg 기반 커널 덤프 분석이 필요합니다.')

    return recommendations



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
        max_panic_like_event_count = self.get_threshold_var('max_panic_like_event_count', default=0, value_type='int')
        failure_keywords_raw = self.get_threshold_var('failure_keywords', default='', value_type='str')

        rc, out, err = self._run_ps(LOG_KERNEL_COMMAND)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'WinRM 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if self._is_not_applicable(rc, err):
            return self.fail(
                'WinRM 실행 환경을 사용할 수 없습니다.',
                message='Windows 커널 로그 점검을 수행할 수 없습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='Windows 커널 로그 점검 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        text = (out or '').strip()
        if not text:
            text = '[]'

        entries = _normalize_entries(text)
        if entries is None:
            return self.fail(
                '커널 로그 파싱 실패',
                message='커널 로그 JSON 결과를 해석하지 못했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        if not entries:
            return self.ok(
                metrics={
                    'panic_like_event_count': 0,
                    'bugcheck_event_count': 0,
                    'kernel_power_41_count': 0,
                    'live_kernel_event_count': 0,
                    'unexpected_shutdown_event_count': 0,
                    'matched_failure_keywords': [],
                    'analysis_recommendations': [],
                },
                thresholds={
                    'max_panic_like_event_count': max_panic_like_event_count,
                    'failure_keywords': [],
                },
                reasons='최근 30일 내 BugCheck, Kernel-Power 41, LiveKernelEvent, 비정상 종료 이벤트가 확인되지 않았습니다.',
                message=(
                    'Windows 커널 로그 점검이 정상입니다. 현재 상태: 최근 30일 내 '
                    '커널 장애성 이벤트가 없어 0건으로 집계했습니다.'
                ),
            )

        failure_keywords = [
            keyword.strip()
            for keyword in failure_keywords_raw.split(',')
            if keyword.strip()
        ]
        serialized_text = json.dumps(entries, ensure_ascii=False)
        matched_failure_keywords = [
            keyword for keyword in failure_keywords if keyword.lower() in serialized_text.lower()
        ]
        if matched_failure_keywords:
            return self.fail(
                '커널 로그 실패 키워드 감지',
                message='커널 로그 결과에서 실패 키워드가 확인되었습니다.',
                stdout=serialized_text,
                stderr=(err or '').strip(),
            )

        bugcheck_entries = [
            entry for entry in entries
            if entry['provider_name'].lower() == 'bugcheck'
            or 'bugcheck' in entry['message'].lower()
        ]
        kernel_power_41_entries = [
            entry for entry in entries
            if entry['provider_name'] == 'Microsoft-Windows-Kernel-Power' and entry['event_id'] == 41
        ]
        live_kernel_entries = [
            entry for entry in entries
            if 'livekernelevent' in entry['message'].lower()
        ]
        unexpected_shutdown_entries = [
            entry for entry in entries
            if entry['provider_name'] == 'EventLog' and entry['event_id'] == 6008
        ]
        bluescreen_entries = [
            entry for entry in entries
            if 'blue screen' in entry['message'].lower() or 'bluescreen' in entry['message'].lower()
        ]

        repeated_event_keys = {}
        for entry in entries:
            key = f"{entry['provider_name']}:{entry['event_id']}"
            repeated_event_keys[key] = repeated_event_keys.get(key, 0) + 1
        repeated_events = [
            f"{key}({count})"
            for key, count in repeated_event_keys.items()
            if count > 1
        ]

        latest_entry = entries[0]
        recommendations = _recommendations(
            entries,
            bugcheck_entries,
            kernel_power_41_entries,
            live_kernel_entries,
            unexpected_shutdown_entries,
        )

        if len(entries) > max_panic_like_event_count:
            return self.fail(
                '커널 장애성 이벤트 감지',
                message=(
                    f'Windows 커널 로그 점검에 실패했습니다. 현재 상태: '
                    f'장애성 이벤트 {len(entries)}건 (기준 {max_panic_like_event_count}건 이하), '
                    f'BugCheck {len(bugcheck_entries)}건, Kernel-Power 41 {len(kernel_power_41_entries)}건, '
                    f'LiveKernelEvent {len(live_kernel_entries)}건, 비정상 종료(EventLog 6008) {len(unexpected_shutdown_entries)}건. '
                    f'권고: {" ".join(recommendations) if recommendations else "추가 분석이 필요합니다."}'
                ),
                stdout=serialized_text,
                stderr=(err or '').strip(),
            )

        return self.ok(
            metrics={
                'panic_like_event_count': len(entries),
                'bugcheck_event_count': len(bugcheck_entries),
                'kernel_power_41_count': len(kernel_power_41_entries),
                'live_kernel_event_count': len(live_kernel_entries),
                'unexpected_shutdown_event_count': len(unexpected_shutdown_entries),
                'bluescreen_event_count': len(bluescreen_entries),
                'latest_event_time': latest_entry['time_created'],
                'latest_event_provider': latest_entry['provider_name'],
                'latest_event_id': latest_entry['event_id'],
                'repeated_events': repeated_events,
                'matched_failure_keywords': matched_failure_keywords,
                'analysis_recommendations': recommendations,
            },
            thresholds={
                'max_panic_like_event_count': max_panic_like_event_count,
                'failure_keywords': failure_keywords,
            },
            reasons=(
                f'Windows 커널 로그 점검이 정상입니다. 현재 상태: '
                f'이벤트 {len(entries)}건 (기준 {max_panic_like_event_count}건 이하), '
                f'BugCheck {len(bugcheck_entries)}건, Kernel-Power 41 {len(kernel_power_41_entries)}건, '
                f'LiveKernelEvent {len(live_kernel_entries)}건, 비정상 종료(EventLog 6008) {len(unexpected_shutdown_entries)}건.'
            ),
            message='최근 30일 내 커널 장애성 이벤트 수가 기준 범위 내입니다.',
        )


CHECK_CLASS = Check
