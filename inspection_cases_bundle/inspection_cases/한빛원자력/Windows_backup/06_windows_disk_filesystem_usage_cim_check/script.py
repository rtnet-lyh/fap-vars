# -*- coding: utf-8 -*-

import json

from items.common._base import BaseCheck


DISK_USAGE_COMMAND = "wmic LogicalDisk where \"DriveType=3\" get DeviceID,Size,FreeSpace /value"


def _parse_float(value):
    return round(float(str(value).strip()), 2)


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
        max_usage_percent = self.get_threshold_var('max_usage_percent', default=80.0, value_type='float')
        min_available_percent = self.get_threshold_var('min_available_percent', default=20.0, value_type='float')
        failure_keywords_raw = self.get_threshold_var('failure_keywords', default='', value_type='str')

        rc, out, err = self._run_ps(_prepare_windows_command(DISK_USAGE_COMMAND))
        if self._is_connection_error(rc, err):
            return self.fail('호스트 연결 실패', message=(err or 'WinRM 연결 확인에 실패했습니다.').strip(), stderr=(err or '').strip())
        if self._is_not_applicable(rc, err):
            return self.fail('WinRM 실행 환경을 사용할 수 없습니다.', message='Windows 디스크 사용률 점검을 수행할 수 없습니다.', stdout=(out or '').strip(), stderr=(err or '').strip())
        if rc != 0:
            return self.fail('점검 명령 실행 실패', message='Windows 디스크 사용률 점검 명령 실행에 실패했습니다.', stdout=(out or '').strip(), stderr=(err or '').strip())

        text = (out or '').strip()
        if not text:
            return self.fail('디스크 사용량 정보 없음', message='디스크 사용률 결과가 비어 있습니다.', stdout='', stderr=(err or '').strip())

        failure_keywords = [keyword.strip() for keyword in failure_keywords_raw.split(',') if keyword.strip()]
        matched_failure_keywords = [keyword for keyword in failure_keywords if keyword.lower() in text.lower()]
        if matched_failure_keywords:
            return self.fail('디스크 실패 키워드 감지', message='디스크 사용률 결과에서 실패 키워드가 확인되었습니다.', stdout=text, stderr=(err or '').strip())

        volumes = []
        current = {}
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                if current:
                    volumes.append(current)
                    current = {}
                continue
            if '=' not in line:
                continue
            key, value = line.split('=', 1)
            current[key.strip()] = value.strip()
        if current:
            volumes.append(current)

        parsed = []
        for volume in volumes:
            try:
                size = float(volume.get('Size', '0') or '0')
                free = float(volume.get('FreeSpace', '0') or '0')
            except ValueError:
                continue
            if size <= 0:
                continue
            usage_percent = round(((size - free) / size) * 100, 2)
            available_percent = round((free / size) * 100, 2)
            parsed.append({
                'mount_point': volume.get('DeviceID', ''),
                'size_gib': round(size / 1024 / 1024 / 1024, 2),
                'used_gib': round((size - free) / 1024 / 1024 / 1024, 2),
                'available_gib': round(free / 1024 / 1024 / 1024, 2),
                'usage_percent': usage_percent,
                'available_percent': available_percent,
            })

        if not parsed:
            return self.fail('디스크 사용량 파싱 실패', message='디스크 사용률 key=value 결과를 해석하지 못했습니다.', stdout=text, stderr=(err or '').strip())

        max_usage_entry = max(parsed, key=lambda item: item['usage_percent'])
        min_available_entry = min(parsed, key=lambda item: item['available_percent'])

        if max_usage_entry['usage_percent'] >= max_usage_percent:
            return self.fail('디스크 사용률 임계치 초과', message='사용률이 기준치를 초과한 볼륨이 확인되었습니다.', stdout=text, stderr=(err or '').strip())
        if min_available_entry['available_percent'] <= min_available_percent:
            return self.fail('디스크 가용률 임계치 미달', message='가용률이 기준치 이하인 볼륨이 확인되었습니다.', stdout=text, stderr=(err or '').strip())

        return self.ok(
            metrics={
                'volume_count': len(parsed),
                'volumes': parsed,
                'max_usage_percent': max_usage_entry['usage_percent'],
                'min_available_percent': min_available_entry['available_percent'],
                'matched_failure_keywords': matched_failure_keywords,
            },
            thresholds={
                'max_usage_percent': max_usage_percent,
                'min_available_percent': min_available_percent,
                'failure_keywords': failure_keywords,
            },
            reasons=(
                f'Windows 디스크 사용률 점검이 정상입니다. 현재 상태: '
                f'볼륨 {len(parsed)}개, 최고 사용률 {max_usage_entry["mount_point"]} '
                f'{max_usage_entry["usage_percent"]:.2f}% (기준 {max_usage_percent:.2f}% 미만), '
                f'최소 가용률 {min_available_entry["mount_point"]} '
                f'{min_available_entry["available_percent"]:.2f}% (기준 {min_available_percent:.2f}% 초과).'
            ),
            message='모든 볼륨 사용률과 가용 공간 비율이 기준 범위 내입니다.',
        )


CHECK_CLASS = Check
