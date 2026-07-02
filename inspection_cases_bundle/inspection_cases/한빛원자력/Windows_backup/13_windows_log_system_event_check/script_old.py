# -*- coding: utf-8 -*-

import json

from items.common._base import BaseCheck


LOG_SYSTEM_COMMAND = "powershell -Command \"Get-EventLog -LogName System -Newest 50 | ForEach-Object { '{0} [{1}] ({2}) {3}' -f $_.TimeGenerated, $_.EntryType, $_.Source, $_.Message.Replace(\\\"`n\\\",' ').Trim().Substring(0, [Math]::Min($_.Message.Length, 80)) }\""


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
        max_critical_error_count = self.get_threshold_var('max_critical_error_count', default=0, value_type='int')
        max_warning_count = self.get_threshold_var('max_warning_count', default=10, value_type='int')
        failure_keywords_raw = self.get_threshold_var('failure_keywords', default='', value_type='str')

        rc, out, err = self._run_ps(_prepare_windows_command(LOG_SYSTEM_COMMAND))
        if self._is_connection_error(rc, err):
            return self.fail('호스트 연결 실패', message=(err or 'WinRM 연결 확인에 실패했습니다.').strip(), stderr=(err or '').strip())
        if self._is_not_applicable(rc, err):
            return self.fail('WinRM 실행 환경을 사용할 수 없습니다.', message='Windows 시스템 로그 점검을 수행할 수 없습니다.', stdout=(out or '').strip(), stderr=(err or '').strip())
        if rc != 0:
            return self.fail('점검 명령 실행 실패', message='Windows 시스템 로그 점검 명령 실행에 실패했습니다.', stdout=(out or '').strip(), stderr=(err or '').strip())

        text = (out or '').strip()
        failure_keywords = [keyword.strip() for keyword in failure_keywords_raw.split(',') if keyword.strip()]
        matched_failure_keywords = [keyword for keyword in failure_keywords if keyword.lower() in text.lower()]
        if matched_failure_keywords:
            return self.fail('시스템 로그 실패 키워드 감지', message='시스템 로그 결과에서 실패 키워드가 확인되었습니다.', stdout=text, stderr=(err or '').strip())
        if not text:
            return self.ok(metrics={'event_count': 0, 'critical_error_count': 0, 'warning_count': 0, 'matched_failure_keywords': []}, thresholds={'max_critical_error_count': max_critical_error_count, 'max_warning_count': max_warning_count, 'failure_keywords': failure_keywords}, reasons='최근 시스템 로그가 없습니다.', message='Windows 시스템 로그 점검이 정상입니다. 최근 시스템 로그가 없습니다.')

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        critical_error_entries = [line for line in lines if '[error]' in line.lower()]
        warning_entries = [line for line in lines if '[warning]' in line.lower()]

        if len(critical_error_entries) > max_critical_error_count:
            return self.fail('시스템 로그 오류 이벤트 임계치 초과', message=f'Windows 시스템 로그 점검에 실패했습니다. 현재 상태: Critical/Error {len(critical_error_entries)}건 (기준 {max_critical_error_count}건 이하), Warning {len(warning_entries)}건.', stdout=text, stderr=(err or '').strip())
        if len(warning_entries) > max_warning_count:
            return self.fail('시스템 로그 경고 이벤트 임계치 초과', message=f'Windows 시스템 로그 점검에 실패했습니다. 현재 상태: Warning {len(warning_entries)}건 (기준 {max_warning_count}건 이하), Critical/Error {len(critical_error_entries)}건.', stdout=text, stderr=(err or '').strip())

        return self.ok(
            metrics={
                'event_count': len(lines),
                'critical_error_count': len(critical_error_entries),
                'warning_count': len(warning_entries),
                'latest_event_line': lines[0] if lines else '',
                'matched_failure_keywords': matched_failure_keywords,
            },
            thresholds={
                '최대 치명 오류 수': max_critical_error_count,
                '최대 경고 수': max_warning_count,
                '실패 키워드': failure_keywords,
            },
            reasons=f'Windows 시스템 로그 점검이 정상입니다. 현재 상태: 이벤트 {len(lines)}건, Critical/Error {len(critical_error_entries)}건, Warning {len(warning_entries)}건.',
            message='최근 시스템 로그의 Error/Critical/Warning 이벤트 수가 기준 범위 내입니다.',
        )


CHECK_CLASS = Check
