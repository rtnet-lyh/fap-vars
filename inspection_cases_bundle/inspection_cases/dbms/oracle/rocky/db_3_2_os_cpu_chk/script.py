# -*- coding: utf-8 -*-

import re
from .common._base import BaseCheck

RESOURCE_KIND = "cpu"
INSPECTION_NAME = "Oracle 프로세스 CPU 사용률"
COMMAND = "ps -eo pid,comm,%cpu --sort=-%cpu | grep ora_ | grep -v grep | head -10"
PROCESS_PATTERN = re.compile("^\\s*(\\d+)\\s+(ora_\\S+)\\s+([0-9]+(?:\\.[0-9]+)?)\\s*$")


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = "paramiko"
    PARAMIKO_PROFILE = "linux"
    PARAMIKO_REUSE_SESSION = False
    DEFAULT_ORACLE_ACCOUNT = "oracle"

    def _failure(
        self, error, message, thresholds, metrics=None, stdout=None, stderr=None
    ):
        return self.fail(error, metrics=metrics or {}, message=message)

    def _parse_processes(self, output):
        processes = []
        for line in str(output or "").splitlines():
            match = PROCESS_PATTERN.match(line)
            if not match:
                continue
            item = {
                "pid": int(match.group(1)),
                "process": match.group(2),
                "usage_percent": float(match.group(3)),
            }
            if RESOURCE_KIND == "memory":
                item["rss_kb"] = int(match.group(4))
                item["vsz_kb"] = int(match.group(5))
            processes.append(item)
        return processes

    def run(self):
        raw_account = self.get_threshold_var(
            "oracle_account", default=self.DEFAULT_ORACLE_ACCOUNT, value_type="str"
        )
        max_usage = self.get_threshold_var(
            "max_usage_percent", default=80.0, value_type="float"
        )
        thresholds = {
            "oracle_account": str(raw_account or "").strip(),
            "max_usage_percent": max_usage,
        }
        oracle_account = str(raw_account or "").strip() or self.DEFAULT_ORACLE_ACCOUNT
        try:
            account_results = self._run_account_commands(
                oracle_account, [{"command": COMMAND, "timeout": 30}]
            )
        except ValueError as exc:
            return self._failure("점검 설정 오류", str(exc), thresholds)
        result = account_results[0] if account_results else {}
        stdout = str(result.get("stdout") or "").strip()
        stderr = str(result.get("stderr") or "").strip()
        verification = (
            getattr(self, "_solaris_last_account_switch_verification", {}) or {}
        )
        metrics = {
            "oracle_account": oracle_account,
            "verified_oracle_account": verification.get("actual_user") or "",
            "become_user": str(
                self._get_preferred_credential_value("become_user", "root") or "root"
            ),
        }
        if result.get("rc") != 0:
            metrics["command_rc"] = result.get("rc")
            lowered = stderr.lower()
            if self._is_connection_error(result.get("rc"), stderr):
                error = "호스트 연결 실패"
                message = "Paramiko 호스트 연결에 실패했습니다."
            elif "권한상승" in stderr or "become" in lowered:
                error = "root 권한 상승 실패"
                message = "root 계정 권한 상승 또는 검증에 실패했습니다."
            elif not verification.get("ok"):
                error = "Oracle 계정 전환 실패"
                message = (
                    verification.get("message") or "Oracle 계정 전환에 실패했습니다."
                )
            else:
                error = "점검 명령 실행 실패"
                message = str(INSPECTION_NAME) + " 명령 실행에 실패했습니다."
            return self._failure(
                error,
                message,
                thresholds,
                metrics=metrics,
                stdout=stdout,
                stderr=stderr,
            )
        processes = self._parse_processes(stdout)
        if not processes:
            return self._failure(
                "출력 파싱 실패",
                "Oracle 프로세스 자원 사용률 행을 해석하지 못했습니다.",
                thresholds,
                metrics=metrics,
                stdout=stdout,
            )
        ordered = sorted(
            processes, key=lambda item: item["usage_percent"], reverse=True
        )
        exceeded = [item for item in ordered if item["usage_percent"] > max_usage]
        metrics.update(
            {
                "process_count": len(processes),
                "max_usage_percent": ordered[0]["usage_percent"],
                "max_usage_process": ordered[0],
                "top_processes": ordered[:10],
                "over_threshold_processes": exceeded,
            }
        )
        if exceeded:
            message = "%s 최대 사용률 %.2f%%가 기준 %.2f%%를 초과했습니다." % (
                INSPECTION_NAME,
                ordered[0]["usage_percent"],
                max_usage,
            )
            return self._failure(
                "자원 사용률 임계치 초과",
                message,
                thresholds,
                metrics=metrics,
                stdout=stdout,
            )
        reason = "%s 최대 사용률 %.2f%%가 기준 %.2f%% 이하입니다." % (
            INSPECTION_NAME,
            ordered[0]["usage_percent"],
            max_usage,
        )
        return self.ok(metrics=metrics, message=reason)


CHECK_CLASS = Check
