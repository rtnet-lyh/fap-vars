# -*- coding: utf-8 -*-

from items.common._base import BaseCheck


KERNAL_PARAMETER_COMMAND = "powershell -Command \"netsh int tcp show global; netsh int ip show global; Get-ItemProperty -Path 'HKLM:\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters'\""



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
        expected_ip_forward = self.get_threshold_var('expected_ip_forward', default='0', value_type='str')
        disallowed_accept_source_route_values_raw = self.get_threshold_var('disallowed_accept_source_route_values', default='0', value_type='str')
        failure_keywords_raw = self.get_threshold_var('failure_keywords', default='', value_type='str')

        rc, out, err = self._run_ps(_prepare_windows_command(KERNAL_PARAMETER_COMMAND))
        if self._is_connection_error(rc, err):
            return self.fail('호스트 연결 실패', message=(err or 'WinRM 연결 확인에 실패했습니다.').strip(), stderr=(err or '').strip())
        if self._is_not_applicable(rc, err):
            return self.fail('WinRM 실행 환경을 사용할 수 없습니다.', message='Windows 커널 파라미터 점검을 수행할 수 없습니다.', stdout=(out or '').strip(), stderr=(err or '').strip())
        if rc != 0:
            return self.fail('점검 명령 실행 실패', message='Windows 커널 파라미터 점검 명령 실행에 실패했습니다.', stdout=(out or '').strip(), stderr=(err or '').strip())

        text = (out or '').strip()
        if not text:
            return self.fail('커널 파라미터 정보 없음', message='커널 파라미터 결과가 비어 있습니다.', stdout='', stderr=(err or '').strip())

        failure_keywords = [keyword.strip() for keyword in failure_keywords_raw.split(',') if keyword.strip()]
        matched_failure_keywords = [keyword for keyword in failure_keywords if keyword.lower() in text.lower()]
        if matched_failure_keywords:
            return self.fail('커널 파라미터 실패 키워드 감지', message='커널 파라미터 결과에서 실패 키워드가 확인되었습니다.', stdout=text, stderr=(err or '').strip())

        ip_enable_router = ''
        hostname = ''
        source_routing_behavior = ''
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if line.startswith('IPEnableRouter'):
                ip_enable_router = line.split(':', 1)[1].strip()
            elif line.startswith('Hostname'):
                hostname = line.split(':', 1)[1].strip()
            elif line.startswith('Source Routing Behavior'):
                source_routing_behavior = line.split(':', 1)[1].strip()

        disallowed_values = [item.strip() for item in disallowed_accept_source_route_values_raw.split(',') if item.strip()]
        if not hostname:
            return self.fail('커널 파라미터 파싱 실패', message='Hostname 값을 해석하지 못했습니다.', stdout=text, stderr=(err or '').strip())
        if ip_enable_router != expected_ip_forward:
            return self.fail('IP forwarding 설정 불일치', message='IPEnableRouter 값이 기대값과 다릅니다.', stdout=text, stderr=(err or '').strip())
        if source_routing_behavior and source_routing_behavior in disallowed_values:
            return self.fail('Source routing 설정 불량', message='Source Routing Behavior 값이 허용되지 않는 값입니다.', stdout=text, stderr=(err or '').strip())

        return self.ok(
            metrics={
                'kernel.hostname': hostname,
                'net.ipv4.ip_forward': ip_enable_router,
                'source_routing_behavior': source_routing_behavior,
                'matched_failure_keywords': matched_failure_keywords,
            },
            thresholds={
                'IP 포워딩 기대값': expected_ip_forward,
                '허용되지 않는 소스 라우팅 값': disallowed_values,
                '실패 키워드': failure_keywords,
            },
            reasons=f'Windows 커널 파라미터 점검이 정상입니다. 현재 상태: Hostname={hostname}, IPEnableRouter={ip_enable_router}, Source Routing Behavior={source_routing_behavior}.',
            message='핵심 네트워크 커널 파라미터가 기준 범위 내입니다.',
        )


CHECK_CLASS = Check
