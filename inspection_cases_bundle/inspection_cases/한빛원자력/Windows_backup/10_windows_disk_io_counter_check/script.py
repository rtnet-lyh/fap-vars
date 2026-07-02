# -*- coding: utf-8 -*-

import json

from items.common._base import BaseCheck


DISK_IO_COMMAND = "powershell -Command \"$p = (Get-Counter -ListSet 'PhysicalDisk').Paths | Where-Object { $_ -like '*Avg. Disk sec/Read' -or $_ -like '*Avg. Disk sec/Write' }; Get-Counter -Counter $p -SampleInterval 1 -MaxSamples 1 | Select-Object -ExpandProperty CounterSamples | Where-Object { $_.Path -like '*(_total)*' } | Select-Object @{Name='Metric'; Expression={if($_.Path -like '*read*') {'Read Latency'} else {'Write Latency'}}}, @{Name='Latency(ms)'; Expression={[Math]::Round($_.CookedValue * 1000, 3)}}\""


def _parse_float(value):
    return round(float(str(value).strip()), 2)


def _parse_int(value):
    return int(str(value).strip())


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
        max_busy_percent = self.get_threshold_var('max_busy_percent', default=80.0, value_type='float')
        min_idle_percent = self.get_threshold_var('min_idle_percent', default=20.0, value_type='float')
        max_wait_ms = self.get_threshold_var('max_wait_ms', default=10.0, value_type='float')
        max_queue_length = self.get_threshold_var('max_queue_length', default=1.0, value_type='float')
        failure_keywords_raw = self.get_threshold_var('failure_keywords', default='', value_type='str')

        rc, out, err = self._run_ps(_prepare_windows_command(DISK_IO_COMMAND))
        if self._is_connection_error(rc, err):
            return self.fail('호스트 연결 실패', message=(err or 'WinRM 연결 확인에 실패했습니다.').strip(), stderr=(err or '').strip())
        if self._is_not_applicable(rc, err):
            return self.fail('WinRM 실행 환경을 사용할 수 없습니다.', message='Windows 디스크 I/O 점검을 수행할 수 없습니다.', stdout=(out or '').strip(), stderr=(err or '').strip())
        if rc != 0:
            return self.fail('점검 명령 실행 실패', message='Windows 디스크 I/O 점검 명령 실행에 실패했습니다.', stdout=(out or '').strip(), stderr=(err or '').strip())

        text = (out or '').strip()
        if not text:
            return self.fail('디스크 I/O 정보 없음', message='디스크 I/O 결과가 비어 있습니다.', stdout='', stderr=(err or '').strip())

        failure_keywords = [keyword.strip() for keyword in failure_keywords_raw.split(',') if keyword.strip()]
        matched_failure_keywords = [keyword for keyword in failure_keywords if keyword.lower() in text.lower()]
        if matched_failure_keywords:
            return self.fail('디스크 I/O 실패 키워드 감지', message='디스크 I/O 결과에서 실패 키워드가 확인되었습니다.', stdout=text, stderr=(err or '').strip())

        latencies = {}
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line or line.startswith('Metric') or line.startswith('------'):
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            try:
                value = float(parts[-1])
            except ValueError:
                continue
            name = ' '.join(parts[:-1])
            latencies[name.lower()] = value

        if not latencies:
            return self.fail('디스크 I/O 파싱 실패', message='디스크 I/O 표 형식을 해석하지 못했습니다.', stdout=text, stderr=(err or '').strip())

        read_latency_ms = latencies.get('read latency', 0.0)
        write_latency_ms = latencies.get('write latency', 0.0)
        max_latency_ms = max(read_latency_ms, write_latency_ms)
        busy_percent = 0.0
        idle_percent = 100.0
        queue_length = 0.0

        if max_latency_ms > max_wait_ms:
            return self.fail('디스크 I/O 대기시간 임계치 초과', message='디스크 읽기/쓰기 지연시간이 기준치를 초과했습니다.', stdout=text, stderr=(err or '').strip())

        return self.ok(
            metrics={
                'busy_percent': busy_percent,
                'idle_percent': idle_percent,
                'wait_ms': max_latency_ms,
                'queue_length': queue_length,
                'read_latency_ms': read_latency_ms,
                'write_latency_ms': write_latency_ms,
                'matched_failure_keywords': matched_failure_keywords,
            },
            thresholds={
                'max_busy_percent': max_busy_percent,
                'min_idle_percent': min_idle_percent,
                'max_wait_ms': max_wait_ms,
                'max_queue_length': max_queue_length,
                'failure_keywords': failure_keywords,
            },
            reasons=f'Windows 디스크 I/O 점검이 정상입니다. 현재 상태: Read {read_latency_ms:.2f}ms, Write {write_latency_ms:.2f}ms, 최대 {max_latency_ms:.2f}ms (기준 {max_wait_ms:.2f}ms 이하).',
            message='디스크 I/O 지연시간이 기준 범위 내입니다.',
        )


CHECK_CLASS = Check
