# -*- coding: utf-8 -*-

import json

from items.common._base import BaseCheck


LOG_HBA_COMMAND = (
    "$OutputEncoding = [System.Text.UTF8Encoding]::new($false); "
    "[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); "
    "$ip=Get-InitiatorPort -ErrorAction SilentlyContinue; "
    "$fc=Get-CimInstance -Namespace root\\wmi -Class MSFC_FibrePortHBAAttributes -ErrorAction SilentlyContinue; "
    "$ev=Get-WinEvent -FilterHashtable @{LogName='System';StartTime=(Get-Date).AddDays(-30);Level=@(1,2,3)} -ErrorAction SilentlyContinue|Where-Object{$_.Message -match '(?i)\\bhba\\b|fibre channel|fiber channel|\\bfc\\b|loopback|link down|port.+offline|port.+online'}; "
    "$result=[ordered]@{"
    "InitiatorPortsExposed=[bool]$ip; "
    "FcPortStateExposed=[bool]$fc; "
    "EventDataExposed=[bool]$ev; "
    "InitiatorPorts=@($ip|Select-Object InstanceName,ConnectionType,NodeAddress,PortAddress); "
    "FcPorts=@($fc|Select-Object InstanceName,@{N='PortState';E={switch($_.Attributes.PortState){1{'Unknown'}2{'Operational'}3{'User Offline'}4{'Bypassed'}5{'Diagnostics'}6{'Link Down'}7{'Port Error'}8{'Loopback'}default{$_.Attributes.PortState}}}},HBAStatus); "
    "Events=@($ev|Select-Object -First 50 TimeCreated,ProviderName,Id,LevelDisplayName,@{N='Message';E={($_.Message -replace '\\r?\\n',' ')}})"
    "}; "
    "$result|ConvertTo-Json -Depth 4"
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
        max_hba_event_count = self.get_threshold_var('max_hba_event_count', default=0, value_type='int')
        failure_keywords_raw = self.get_threshold_var('failure_keywords', default='', value_type='str')

        rc, out, err = self._run_ps(LOG_HBA_COMMAND)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'WinRM 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if self._is_not_applicable(rc, err):
            return self.fail(
                'WinRM 실행 환경을 사용할 수 없습니다.',
                message='Windows HBA 로그 점검을 수행할 수 없습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='Windows HBA 로그 점검 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        text = (out or '').strip()
        if not text:
            return self.fail(
                'HBA 로그 출력 없음',
                message='HBA 포트 또는 이벤트 로그 점검 결과가 비어 있습니다.',
                stdout='',
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
                'HBA 로그 실패 키워드 감지',
                message='HBA 로그 결과에서 실패 키워드가 확인되었습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return self.fail(
                'HBA 로그 파싱 실패',
                message='HBA 포트 또는 이벤트 로그 JSON을 해석하지 못했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        no_initiator_ports = not bool(parsed.get('InitiatorPortsExposed')) if isinstance(parsed, dict) else True
        no_fc_port_state = not bool(parsed.get('FcPortStateExposed')) if isinstance(parsed, dict) else True
        no_hba_events = not bool(parsed.get('EventDataExposed')) if isinstance(parsed, dict) else True

        initiator_ports = _as_list(parsed.get('InitiatorPorts', [])) if isinstance(parsed, dict) else []
        initiator_port_count = len([entry for entry in initiator_ports if isinstance(entry, dict)])

        fc_port_entries = []
        for entry in _as_list(parsed.get('FcPorts', [])) if isinstance(parsed, dict) else []:
            if not isinstance(entry, dict):
                continue
            fc_port_entries.append({
                'instance_name': str(entry.get('InstanceName', '')).strip(),
                'port_state': str(entry.get('PortState', '')).strip(),
                'hba_status': str(entry.get('HBAStatus', '')).strip(),
            })

        event_entries = []
        for entry in _as_list(parsed.get('Events', [])) if isinstance(parsed, dict) else []:
            if not isinstance(entry, dict):
                continue
            event_id = entry.get('Id', '')
            event_entries.append({
                'time_created': str(entry.get('TimeCreated', '')).strip(),
                'provider_name': str(entry.get('ProviderName', '')).strip(),
                'event_id': _parse_int(event_id) if str(event_id).strip() else '',
                'level': str(entry.get('LevelDisplayName', '')).strip(),
                'message': str(entry.get('Message', '')).strip(),
            })

        abnormal_port_entries = []
        for entry in fc_port_entries:
            port_state = entry['port_state'].lower()
            hba_status = entry['hba_status'].lower()
            if port_state and port_state not in ('operational', 'loopback'):
                abnormal_port_entries.append(entry)
                continue
            if hba_status and hba_status not in ('hba_status_ok', 'ok', '0'):
                abnormal_port_entries.append(entry)

        if abnormal_port_entries:
            return self.fail(
                'HBA 포트 상태 이상 감지',
                message='HBA 포트 상태 또는 HBAStatus가 정상 범위를 벗어났습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        if len(event_entries) > max_hba_event_count:
            return self.fail(
                'HBA 로그 이벤트 감지',
                message='최근 30일 내 HBA 관련 경고/오류 이벤트가 기준치를 초과했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        if no_initiator_ports or no_fc_port_state:
            return self.fail(
                'HBA 포트 정보 미노출',
                message='Windows HBA 로그 점검에 실패했습니다. 현재 상태: HBA initiator 또는 FC 포트 상태 정보를 확인할 수 없습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        latest_event = event_entries[0] if event_entries else {}
        operational_port_count = sum(1 for entry in fc_port_entries if entry['port_state'].lower() == 'operational')
        loopback_port_count = sum(1 for entry in fc_port_entries if entry['port_state'].lower() == 'loopback')

        reasons = 'HBA 포트 상태와 최근 30일 이벤트 로그를 점검한 결과 이상 징후가 없습니다.'

        return self.ok(
            metrics={
                'initiator_port_count': initiator_port_count,
                'fc_port_count': len(fc_port_entries),
                'operational_port_count': operational_port_count,
                'loopback_port_count': loopback_port_count,
                'abnormal_port_count': len(abnormal_port_entries),
                'hba_event_count': len(event_entries),
                'initiator_ports_exposed': not no_initiator_ports,
                'fc_port_state_exposed': not no_fc_port_state,
                'latest_event_time': latest_event.get('time_created', ''),
                'latest_event_provider': latest_event.get('provider_name', ''),
                'latest_event_id': latest_event.get('event_id', ''),
                'matched_failure_keywords': matched_failure_keywords,
            },
            thresholds={
                'max_hba_event_count': max_hba_event_count,
                'failure_keywords': failure_keywords,
            },
            reasons=(
                f'Windows HBA 로그 점검이 정상입니다. 현재 상태: '
                f'initiator 포트 {initiator_port_count}개, FC 포트 {len(fc_port_entries)}개, '
                f'Operational {operational_port_count}개, Loopback {loopback_port_count}개, '
                f'이벤트 {len(event_entries)}건 (기준 {max_hba_event_count}건 이하).'
            ),
            message=reasons,
        )


CHECK_CLASS = Check
