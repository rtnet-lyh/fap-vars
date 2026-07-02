# -*- coding: utf-8 -*-

import json

from items.common._base import BaseCheck


MEMORY_STATUS_COMMAND = "wmic memorychip get BankLabel,Capacity,ConfiguredClockSpeed,Speed,Status /value"


def _parse_float(value):
    return round(float(value), 2)


def _parse_int(value):
    return int(str(value).strip())


def _parse_optional_int(value, default=0):
    if value in (None, ''):
        return default
    text = str(value).strip()
    if not text or text.lower() == 'none':
        return default
    return int(text)


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
        min_installed_memory_gib = self.get_threshold_var('min_installed_memory_gib', default=8.0, value_type='float')
        failure_keywords_raw = self.get_threshold_var('failure_keywords', default='', value_type='str')

        rc, out, err = self._run_ps(_prepare_windows_command(MEMORY_STATUS_COMMAND))
        if self._is_connection_error(rc, err):
            return self.fail('호스트 연결 실패', message=(err or 'WinRM 연결 확인에 실패했습니다.').strip(), stderr=(err or '').strip())
        if self._is_not_applicable(rc, err):
            return self.fail('WinRM 실행 환경을 사용할 수 없습니다.', message='Windows 메모리 인식 상태 점검을 수행할 수 없습니다.', stdout=(out or '').strip(), stderr=(err or '').strip())
        if rc != 0:
            return self.fail('점검 명령 실행 실패', message='Windows 메모리 상태 점검 명령 실행에 실패했습니다.', stdout=(out or '').strip(), stderr=(err or '').strip())

        text = (out or '').strip()
        if not text:
            return self.fail('메모리 상태 정보 없음', message='메모리 상태 결과가 비어 있습니다.', stdout='', stderr=(err or '').strip())

        failure_keywords = [keyword.strip() for keyword in failure_keywords_raw.split(',') if keyword.strip()]
        matched_failure_keywords = [keyword for keyword in failure_keywords if keyword.lower() in text.lower()]
        if matched_failure_keywords:
            return self.fail('메모리 점검 실패 키워드 감지', message='메모리 상태 결과에서 실패 키워드가 확인되었습니다.', stdout=text, stderr=(err or '').strip())

        modules = []
        current = {}
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                if current:
                    modules.append(current)
                    current = {}
                continue
            if '=' not in line:
                continue
            key, value = line.split('=', 1)
            current[key.strip()] = value.strip()
        if current:
            modules.append(current)

        valid_modules = []
        for module in modules:
            try:
                capacity = int(module.get('Capacity', '0') or '0')
            except ValueError:
                continue
            if capacity <= 0:
                continue
            valid_modules.append({
                'bank_label': module.get('BankLabel', ''),
                'capacity_gib': round(capacity / 1024 / 1024 / 1024, 2),
                'configured_clock_speed_mhz': int(module.get('ConfiguredClockSpeed', '0') or '0') if str(module.get('ConfiguredClockSpeed', '')).strip().isdigit() else 0,
                'speed_mhz': int(module.get('Speed', '0') or '0') if str(module.get('Speed', '')).strip().isdigit() else 0,
                'status': module.get('Status', ''),
            })

        if not valid_modules:
            return self.fail('메모리 모듈 정보 파싱 실패', message='설치된 메모리 모듈 정보를 해석하지 못했습니다.', stdout=text, stderr=(err or '').strip())

        installed_memory_gib = round(sum(m['capacity_gib'] for m in valid_modules), 2)
        module_count = len(valid_modules)
        max_speed_mhz = max((m['speed_mhz'] for m in valid_modules), default=0)

        if installed_memory_gib < min_installed_memory_gib:
            return self.fail('설치 메모리 용량 부족', message=f'설치된 메모리 총 용량이 기준치 미만입니다. 현재 {installed_memory_gib:.2f}GiB, 기준 {min_installed_memory_gib:.2f}GiB 이상 필요합니다.', stdout=text, stderr=(err or '').strip())

        return self.ok(
            metrics={
                'installed_memory_gib': installed_memory_gib,
                'module_count': module_count,
                'max_speed_mhz': max_speed_mhz,
                'modules': valid_modules,
                'matched_failure_keywords': matched_failure_keywords,
            },
            thresholds={
                'min_installed_memory_gib': min_installed_memory_gib,
                'failure_keywords': failure_keywords,
            },
            reasons=f'Windows 메모리 인식 상태 점검이 정상입니다. 현재 상태: 모듈 {module_count}개, 총 {installed_memory_gib:.2f}GiB (기준 {min_installed_memory_gib:.2f}GiB 이상), 최대 속도 {max_speed_mhz}MHz.',
            message='설치 메모리 모듈 수와 총 용량이 기준 범위 내입니다.',
        )


CHECK_CLASS = Check
