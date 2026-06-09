# -*- coding: utf-8 -*-

import re
from .common._base import BaseCheck

COMMAND = 'sqlplus -S /nolog <<\'EOF\'\nCONNECT / AS SYSDBA\nSELECT value AS "Max Processes", (SELECT COUNT(*) FROM v$session) AS "Current Sessions", ROUND((SELECT COUNT(*) FROM v$session) / value * 100, 2) AS "Usage %" FROM v$parameter WHERE name = \'processes\';\nEXIT;\nEOF'


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

    def _sql_errors(self, output):
        return sorted(
            set(re.findall("\\b(?:ORA|SP2|TNS|RMAN)-\\d+\\b", str(output or ""), re.I))
        )

    def _parse_usage(self, output):
        max_processes = None
        current_sessions = None
        usage_percent = None
        for line in str(output or "").splitlines():
            stripped = line.strip()
            if max_processes is None and re.match("^\\d+$", stripped):
                max_processes = int(stripped)
                continue
            match = re.match("^(\\d+)\\s+([0-9]+(?:\\.[0-9]+)?)$", stripped)
            if match and max_processes is not None:
                current_sessions = int(match.group(1))
                usage_percent = float(match.group(2))
                break
        if max_processes is None or current_sessions is None or usage_percent is None:
            return None
        return (max_processes, current_sessions, usage_percent)

    def run(self):
        raw_account = self.get_threshold_var(
            "oracle_account", default=self.DEFAULT_ORACLE_ACCOUNT, value_type="str"
        )
        max_usage = self.get_threshold_var(
            "max_usage_percent", default=90.0, value_type="float"
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
                message = (
                    str("Oracle processes 사용률 조회") + " 명령 실행에 실패했습니다."
                )
            return self._failure(
                error,
                message,
                thresholds,
                metrics=metrics,
                stdout=stdout,
                stderr=stderr,
            )
        sql_errors = self._sql_errors(stdout)
        if sql_errors:
            metrics["sqlplus_error_codes"] = sql_errors
            return self._failure(
                "점검 명령 실행 실패",
                "SQLPlus 오류 코드가 확인되었습니다: " + ", ".join(sql_errors),
                thresholds,
                metrics=metrics,
                stdout=stdout,
            )
        parsed = self._parse_usage(stdout)
        if not parsed:
            return self._failure(
                "출력 파싱 실패",
                "Max Processes, Current Sessions, Usage % 값을 해석하지 못했습니다.",
                thresholds,
                metrics=metrics,
                stdout=stdout,
            )
        (max_processes, current_sessions, usage_percent) = parsed
        metrics.update(
            {
                "max_processes": max_processes,
                "current_sessions": current_sessions,
                "usage_percent": usage_percent,
            }
        )
        if usage_percent > max_usage:
            reason = "현재 세션 사용률 %.2f%%가 기준 %.2f%%를 초과했습니다." % (
                usage_percent,
                max_usage,
            )
            return self._failure(
                "프로세스 사용률 임계치 초과",
                reason,
                thresholds,
                metrics=metrics,
                stdout=stdout,
            )
        reason = "현재 세션 사용률 %.2f%%가 기준 %.2f%% 이하입니다." % (
            usage_percent,
            max_usage,
        )
        return self.ok(metrics=metrics, message=reason)


CHECK_CLASS = Check
