# -*- coding: utf-8 -*-

import re

from items.common._base import BaseCheck


DISK_HA_COMMAND = "powershell.exe -NoProfile -Command \"$cmd = Get-Command Get-VirtualDisk -ErrorAction SilentlyContinue; if (-not $cmd) { 'NOT_APPLICABLE=Get-VirtualDisk unavailable'; exit 0 }; try { $vds = Get-VirtualDisk -ErrorAction Stop } catch { 'Access is denied'; exit 0 }; if (-not $vds) { 'NOT_APPLICABLE=No virtual disk'; exit 0 }; foreach ($vd in $vds) {\n  'Name=' + $vd.FriendlyName;\n  'Resiliency=' + $vd.ResiliencySettingName;\n  'HealthStatus=' + $vd.HealthStatus;\n  'OperationalStatus=' + (($vd.OperationalStatus -join ','));\n  ''\n}\"\n"


def _parse_int(value):
    return int(str(value).strip())



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
        'require_spare_device': '?? ??? ?? ??',
        'max_iuse_percent': 'inode ?? ??? ?? ??',
        'expected_mount_path': '?? ??? ??',
        'expected_mode': '?? ??',
    }
    return direct.get(text, text)

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
        require_spare_device = self.get_threshold_var('require_spare_device', default=0, value_type='int')
        failure_keywords_raw = self.get_threshold_var('failure_keywords', default='', value_type='str')

        rc, out, err = self._run_ps(_prepare_windows_command(DISK_HA_COMMAND))
        if self._is_connection_error(rc, err):
            return self.fail('호스트 연결 실패', message=(err or 'WinRM 연결 확인에 실패했습니다.').strip(), stderr=(err or '').strip())
        text = (out or '').strip()
        stderr_text = (err or '').strip()

        if self._is_not_applicable(rc, err) or text.startswith('NOT_APPLICABLE='):
            return self.not_applicable(message='Storage Spaces 또는 가상 디스크 구성이 없어 디스크 HA 점검 대상이 아닙니다.', raw_output=text or stderr_text)
        if rc != 0:
            return self.fail('점검 명령 실행 실패', message='Windows 디스크 HA 점검 명령 실행에 실패했습니다.', stdout=text, stderr=stderr_text)

        failure_keywords = [keyword.strip() for keyword in failure_keywords_raw.split(',') if keyword.strip()]
        matched_failure_keywords = [keyword for keyword in failure_keywords if keyword.lower() in text.lower()]
        if matched_failure_keywords:
            return self.fail('디스크 HA 실패 키워드 감지', message='디스크 HA 결과에서 실패 키워드가 확인되었습니다.', stdout=text, stderr=stderr_text)

        entries = []
        current = {}
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                if current:
                    entries.append(current)
                    current = {}
                continue
            if '=' not in line:
                continue
            key, value = line.split('=', 1)
            current[key.strip()] = value.strip()
        if current:
            entries.append(current)

        if not entries:
            return self.fail('디스크 HA 파싱 실패', message='가상 디스크 상태 결과를 해석하지 못했습니다.', stdout=text, stderr=stderr_text)

        degraded = [e for e in entries if e.get('HealthStatus', '').lower() not in ('healthy', 'ok') or 'ok' not in e.get('OperationalStatus', 'ok').lower() and 'completed' not in e.get('OperationalStatus', 'ok').lower()]
        spare_count = sum(1 for e in entries if e.get('Resiliency', '').lower() == 'spare')
        if require_spare_device and spare_count < require_spare_device:
            return self.warn(metrics={'virtual_disk_count': len(entries), 'spare_count': spare_count, 'entries': entries, 'matched_failure_keywords': matched_failure_keywords}, thresholds={'require_spare_device': require_spare_device, 'failure_keywords': failure_keywords}, reasons='예비 디스크 수가 기준치 미만입니다.', message='예비 디스크 수가 기준치 미만입니다.')
        if degraded:
            return self.fail('디스크 HA 상태 이상 감지', message='HealthStatus 또는 OperationalStatus가 비정상인 가상 디스크가 확인되었습니다.', stdout=text, stderr=stderr_text)

        return self.ok(metrics={'virtual_disk_count': len(entries), 'spare_count': spare_count, 'entries': entries, 'matched_failure_keywords': matched_failure_keywords}, thresholds={'require_spare_device': require_spare_device, 'failure_keywords': failure_keywords}, reasons=f'Windows 디스크 HA 점검이 정상입니다. 현재 상태: 가상 디스크 {len(entries)}개, spare {spare_count}개.', message='가상 디스크 HA 상태가 기준 범위 내입니다.')


CHECK_CLASS = Check
