# -*- coding: utf-8 -*-

import re

from items.common._base import BaseCheck


OS_PATH_HA_COMMAND = "powershell.exe -NoProfile -Command \"$cmd = Get-Command Get-MPIOPath -ErrorAction SilentlyContinue; if (-not $cmd) { 'NOT_APPLICABLE=Get-MPIOPath unavailable'; exit 0 }; $paths = Get-MPIOPath; if (-not $paths) { 'NOT_APPLICABLE=No MPIO path'; exit 0 }; $paths | Group-Object InstanceName | ForEach-Object {\n  'Name=' + $_.Name;\n  'PathCount=' + $_.Count;\n  'ActivePaths=' + (($_.Group | Where-Object { $_.PathState -match 'Active|Up|Online' }).Count);\n  'State=' + ((($_.Group | Select-Object -ExpandProperty PathState -Unique) -join ','));\n  ''\n}\"\n"



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
        expected_policy_keyword = self.get_threshold_var('expected_policy_keyword', default='round', value_type='str')
        failure_keywords_raw = self.get_threshold_var('failure_keywords', default='', value_type='str')

        rc, out, err = self._run_ps(_prepare_windows_command(OS_PATH_HA_COMMAND))

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'WinRM 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if self._is_not_applicable(rc, err):
            return self.fail(
                'WinRM 실행 환경을 사용할 수 없습니다.',
                message='Windows MPIO 경로 이중화 점검을 수행할 수 없습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='Windows MPIO 경로 이중화 점검 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        text = (out or '').strip()
        if not text or text == 'MPIO 미설치 또는 미지원':
            return self.fail(
                'MPIO 미설치 또는 미지원',
                message=(
                    'Windows MPIO 경로 이중화 점검에 실패했습니다. '
                    '현재 상태: MPIO가 설치되어 있지 않거나 지원되지 않아 '
                    'active 유사 경로 0개, failed 유사 경로 0개로 집계했습니다.'
                ),
                stdout=text,
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
                'MPIO 실패 키워드 감지',
                message='MPIO 경로 이중화 결과에서 실패 키워드가 확인되었습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        info = {}
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or ':' not in stripped:
                continue
            key, value = stripped.split(':', 1)
            info[key.strip()] = value.strip()

        lower_text = text.lower()
        active_path_like_count = len(re.findall(r'\bactive\b|\brunning\b', lower_text))
        enabled_path_like_count = len(re.findall(r'\benabled\b|\bstandby\b', lower_text))
        failed_path_like_count = len(re.findall(r'\bfailed\b|\bfaulty\b|\boffline\b', lower_text))
        load_balance_policy = str(info.get('LoadBalancePolicy', '')).strip()

        if failed_path_like_count > 0:
            return self.fail(
                'MPIO 경로 상태 이상 감지',
                message='failed, faulty 또는 offline 상태로 보이는 경로가 확인되었습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        if expected_policy_keyword and load_balance_policy:
            if expected_policy_keyword.lower() not in load_balance_policy.lower():
                return self.fail(
                    'MPIO 부하분산 정책 불일치',
                    message='MPIO 부하분산 정책이 기대한 정책과 일치하지 않습니다.',
                    stdout=text,
                    stderr=(err or '').strip(),
                )

        return self.ok(
            metrics={
                'mpio_installed': True,
                'path_verification_state': info.get('PathVerificationState', ''),
                'path_verification_period': info.get('PathVerificationPeriod', ''),
                'retry_count': info.get('RetryCount', ''),
                'retry_interval': info.get('RetryInterval', ''),
                'disk_timeout_value': info.get('DiskTimeoutValue', ''),
                'load_balance_policy': load_balance_policy,
                'active_path_like_count': active_path_like_count,
                'enabled_path_like_count': enabled_path_like_count,
                'failed_path_like_count': failed_path_like_count,
                'matched_failure_keywords': matched_failure_keywords,
            },
            thresholds={
                '정책 기대 키워드': expected_policy_keyword,
                '실패 키워드': failure_keywords,
            },
            reasons=(
                f'Windows MPIO 경로 이중화 점검이 정상입니다. 현재 상태: '
                f'load_balance_policy={load_balance_policy or "N/A"}, '
                f'active 유사 경로 {active_path_like_count}개, enabled/standby 유사 경로 {enabled_path_like_count}개, '
                f'failed/faulty/offline 유사 경로 {failed_path_like_count}개.'
            ),
            message='MPIO 구성과 경로 상태를 점검한 결과 비정상 경로 징후가 확인되지 않았습니다.',
        )


CHECK_CLASS = Check
