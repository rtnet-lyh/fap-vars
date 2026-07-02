# -*- coding: utf-8 -*-

import json

from items.common._base import BaseCheck


LOG_MEMORY_COMMAND = (
    "$OutputEncoding = [System.Text.UTF8Encoding]::new($false); "
    "[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); "
    "$e=Get-WinEvent -FilterHashtable @{LogName='System';StartTime=(Get-Date).AddDays(-30);Level=@(1,2,3)} -ErrorAction SilentlyContinue | "
    "Where-Object { $_.ProviderName -eq 'Microsoft-Windows-WHEA-Logger' -or $_.Message -match '(?i)\\becc\\b|memory error|single-bit|multi-bit|uncorrectable' }; "
    "if($e){@($e | Select-Object TimeCreated,ProviderName,Id,LevelDisplayName,@{N='Message';E={($_.Message -replace '\\r?\\n',' ')}}) | ConvertTo-Json -Depth 4}else{'No ECC/memory-error-like events found in the last 30 days.'}"
)


def _parse_int(value):
    return int(str(value).strip())


def _as_list(value):
    if isinstance(value, list):
        return value
    if value in (None, ''):
        return []
    return [value]


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
        max_memory_error_event_count = self.get_threshold_var('max_memory_error_event_count', default=0, value_type='int')
        failure_keywords_raw = self.get_threshold_var('failure_keywords', default='', value_type='str')

        rc, out, err = self._run_ps(LOG_MEMORY_COMMAND)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'WinRM 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if self._is_not_applicable(rc, err):
            return self.fail(
                'WinRM 실행 환경을 사용할 수 없습니다.',
                message='Windows 메모리 로그 점검을 수행할 수 없습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='Windows 메모리 오류 로그 점검 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        text = (out or '').strip()
        if not text or 'No ECC/memory-error-like events found in the last 30 days.' in text:
            return self.ok(
                metrics={
                    'memory_error_event_count': 0,
                    'ecc_event_count': 0,
                    'single_bit_event_count': 0,
                    'multi_bit_event_count': 0,
                    'uncorrectable_event_count': 0,
                    'matched_failure_keywords': [],
                },
                thresholds={
                    'max_memory_error_event_count': max_memory_error_event_count,
                    'failure_keywords': [],
                },
                reasons='최근 30일 내 ECC/메모리 오류 관련 이벤트가 확인되지 않았습니다.',
                message=(
                    'Windows 메모리 오류 로그 점검이 정상입니다. '
                    '현재 상태: 최근 30일 내 ECC/메모리 오류 관련 이벤트가 없어 0건으로 집계했습니다.'
                ),
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
                '메모리 로그 실패 키워드 감지',
                message='메모리 로그 결과에서 실패 키워드가 확인되었습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        try:
            raw_entries = json.loads(text)
        except json.JSONDecodeError:
            return self.fail(
                '메모리 로그 파싱 실패',
                message='ECC/메모리 오류 관련 이벤트 JSON을 해석하지 못했습니다.',
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
                'provider_name': str(entry.get('ProviderName', '')).strip(),
                'event_id': _parse_int(event_id) if str(event_id).strip() else 0,
                'level': str(entry.get('LevelDisplayName', '')).strip(),
                'message': str(entry.get('Message', '')).strip(),
            })

        if not entries:
            return self.fail(
                '메모리 로그 파싱 실패',
                message='ECC/메모리 오류 관련 이벤트 항목을 해석하지 못했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        ecc_entries = [entry for entry in entries if 'ecc' in entry['message'].lower()]
        single_bit_entries = [entry for entry in entries if 'single-bit' in entry['message'].lower()]
        multi_bit_entries = [entry for entry in entries if 'multi-bit' in entry['message'].lower()]
        uncorrectable_entries = [entry for entry in entries if 'uncorrectable' in entry['message'].lower()]
        latest_entry = entries[0]

        if len(entries) > max_memory_error_event_count:
            return self.fail(
                '메모리 오류 로그 이벤트 감지',
                message='최근 30일 내 ECC/메모리 오류 관련 이벤트가 기준치를 초과했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        return self.ok(
            metrics={
                'memory_error_event_count': len(entries),
                'ecc_event_count': len(ecc_entries),
                'single_bit_event_count': len(single_bit_entries),
                'multi_bit_event_count': len(multi_bit_entries),
                'uncorrectable_event_count': len(uncorrectable_entries),
                'latest_event_time': latest_entry['time_created'],
                'latest_event_provider': latest_entry['provider_name'],
                'latest_event_id': latest_entry['event_id'],
                'matched_failure_keywords': matched_failure_keywords,
            },
            thresholds={
                'max_memory_error_event_count': max_memory_error_event_count,
                'failure_keywords': failure_keywords,
            },
            reasons='최근 30일 내 ECC/메모리 오류 관련 이벤트 수가 기준 범위 내입니다.',
            message=(
                f'Windows 메모리 오류 로그 점검이 정상입니다. 현재 상태: '
                f'이벤트 {len(entries)}건 (기준 {max_memory_error_event_count}건 이하), '
                f'ECC {len(ecc_entries)}건, Single-bit {len(single_bit_entries)}건, '
                f'Multi-bit {len(multi_bit_entries)}건, Uncorrectable {len(uncorrectable_entries)}건.'
            ),
        )


CHECK_CLASS = Check
