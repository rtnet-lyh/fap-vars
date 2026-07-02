# -*- coding: utf-8 -*-

import json

from items.common._base import BaseCheck


NETWORK_LINK_STATUS_COMMAND = "wmic nic where \"PhysicalAdapter=True\" get Name,NetConnectionID,NetConnectionStatus,NetEnabled,Speed,AdapterType,PhysicalAdapter /format:list"

STATUS_MAP = {
    'up': 'Up',
    'down': 'Down',
    'unknown': 'Unknown',
    'not present': 'Not Present',
}


def _normalize_status(value):
    return STATUS_MAP.get(str(value).strip().lower(), str(value).strip())


def _parse_adapter_entry(entry):
    if not isinstance(entry, dict):
        return None

    name = str(entry.get('Name', '')).strip()
    interface_description = str(entry.get('InterfaceDescription', '')).strip()
    status = _normalize_status(entry.get('Status', ''))
    link_speed = str(entry.get('LinkSpeed', '')).strip()

    if not name and not interface_description and not status and not link_speed:
        return None

    return {
        'name': name,
        'interface_description': interface_description,
        'status': status,
        'link_speed': link_speed,
    }



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
        min_up_physical_nic_count = self.get_threshold_var('min_up_physical_nic_count', default=1, value_type='int')
        failure_keywords_raw = self.get_threshold_var('failure_keywords', default='', value_type='str')

        rc, out, err = self._run_ps(_prepare_windows_command(NETWORK_LINK_STATUS_COMMAND))
        if self._is_connection_error(rc, err):
            return self.fail('호스트 연결 실패', message=(err or 'WinRM 연결 확인에 실패했습니다.').strip(), stderr=(err or '').strip())
        if self._is_not_applicable(rc, err):
            return self.fail('WinRM 실행 환경을 사용할 수 없습니다.', message='Windows NIC 링크 상태 점검을 수행할 수 없습니다.', stdout=(out or '').strip(), stderr=(err or '').strip())
        if rc != 0:
            return self.fail('점검 명령 실행 실패', message='Windows 네트워크 링크 상태 점검 명령 실행에 실패했습니다.', stdout=(out or '').strip(), stderr=(err or '').strip())

        text = (out or '').strip()
        if not text:
            return self.fail('물리 NIC 정보 없음', message='물리 NIC 링크 상태 결과가 비어 있습니다.', stdout='', stderr=(err or '').strip())

        failure_keywords = [keyword.strip() for keyword in failure_keywords_raw.split(',') if keyword.strip()]
        matched_failure_keywords = [keyword for keyword in failure_keywords if keyword.lower() in text.lower()]
        if matched_failure_keywords:
            return self.fail('물리 NIC 실패 키워드 감지', message='물리 NIC 링크 상태 결과에서 실패 키워드가 확인되었습니다.', stdout=text, stderr=(err or '').strip())

        adapters = []
        current = {}
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line or '=' not in line:
                continue
            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip()
            if key == 'AdapterType' and current:
                adapters.append(current)
                current = {}
            current[key] = value
        if current:
            adapters.append(current)

        parsed = []
        status_map = {'0': 'Disconnected', '1': 'Connecting', '2': 'Up', '3': 'Disconnecting', '4': 'Hardware Not Present', '5': 'Hardware Disabled', '6': 'Hardware Malfunction', '7': 'Media Disconnected', '8': 'Authenticating', '9': 'Authentication Succeeded', '10': 'Authentication Failed', '11': 'Invalid Address', '12': 'Credentials Required'}
        for adapter in adapters:
            if str(adapter.get('PhysicalAdapter', '')).strip().lower() != 'true':
                continue
            status_code = str(adapter.get('NetConnectionStatus', '')).strip()
            parsed.append({
                'name': adapter.get('Name', ''),
                'net_connection_id': adapter.get('NetConnectionID', ''),
                'status': status_map.get(status_code, 'Unknown'),
                'link_speed': adapter.get('Speed', ''),
            })

        if not parsed:
            return self.fail('물리 NIC 파싱 실패', message='물리 NIC 링크 상태 결과를 해석하지 못했습니다.', stdout=text, stderr=(err or '').strip())

        up_adapters = [adapter for adapter in parsed if adapter['status'] == 'Up']
        down_adapters = [adapter for adapter in parsed if adapter['status'] not in ('Up', 'Hardware Not Present')]
        not_present_adapters = [adapter for adapter in parsed if adapter['status'] == 'Hardware Not Present']

        if len(up_adapters) < min_up_physical_nic_count:
            return self.fail('활성 물리 NIC 부족', message='Up 상태의 물리 NIC 수가 기준치 미만입니다.', stdout=text, stderr=(err or '').strip())
        if down_adapters:
            return self.fail('물리 NIC Down 상태 감지', message='비정상 상태의 물리 NIC가 확인되었습니다.', stdout=text, stderr=(err or '').strip())

        return self.ok(
            metrics={
                'physical_nic_count': len(parsed),
                'up_physical_nic_count': len(up_adapters),
                'down_physical_nic_count': len(down_adapters),
                'unknown_physical_nic_count': 0,
                'not_present_physical_nic_count': len(not_present_adapters),
                'up_nic_names': [adapter['name'] for adapter in up_adapters],
                'not_present_nic_names': [adapter['name'] for adapter in not_present_adapters],
                'link_speeds': {adapter['name']: adapter['link_speed'] for adapter in parsed},
                'matched_failure_keywords': matched_failure_keywords,
            },
            thresholds={
                '최소 활성 물리 NIC 수': min_up_physical_nic_count,
                '실패 키워드': failure_keywords,
            },
            reasons=f'물리 NIC {len(parsed)}개, Up {len(up_adapters)}개 (기준 {min_up_physical_nic_count}개 이상), Not Present {len(not_present_adapters)}개.',
            message='물리 NIC의 링크 상태를 점검한 결과 Up 상태의 어댑터가 확인되었고 비정상 상태는 없습니다.',
        )


CHECK_CLASS = Check
