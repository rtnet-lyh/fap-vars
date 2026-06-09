# -*- coding: utf-8 -*-

import re
import shlex
from .common._base import BaseCheck

INSPECTION_NAME = "DB 엔진 로그 파일 점검"
DEFAULT_LOG_PATH = "/koem/oracle/diag/rdbms/unidev/UNIDEV/trace/alert_UNIDEV.log"
DEFAULT_FATAL_PATTERNS = "ORA-12012|ORA-00600|ORA-07445|ORA-04031|ORA-01578|ORA-00060|cannot allocate new log"


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = "paramiko"
    PARAMIKO_PROFILE = "linux"
    PARAMIKO_REUSE_SESSION = False
    DEFAULT_ORACLE_ACCOUNT = "oracle"

    def _validate_absolute_path(self, value, name):
        text = str(value or "").strip()
        if not re.match("^/[A-Za-z0-9_./-]+$", text):
            raise ValueError(name + " 값이 안전한 절대 경로가 아닙니다: " + text)
        return text

    def _parse_list(self, value):
        values = []
        seen = set()
        for token in re.split("[|,]+", str(value or "")):
            item = token.strip()
            if not item or item.lower() in seen:
                continue
            seen.add(item.lower())
            values.append(item)
        return values

    def _failure(
        self, error, message, thresholds, metrics=None, stdout=None, stderr=None
    ):
        return self.fail(error, metrics=metrics or {}, message=message)

    def run(self):
        raw_account = self.get_threshold_var(
            "oracle_account", default=self.DEFAULT_ORACLE_ACCOUNT, value_type="str"
        )
        raw_path = self.get_threshold_var(
            "log_path", default=DEFAULT_LOG_PATH, value_type="str"
        )
        raw_patterns = self.get_threshold_var(
            "fatal_error_patterns", default=DEFAULT_FATAL_PATTERNS, value_type="str"
        )
        patterns = self._parse_list(raw_patterns)
        thresholds = {
            "oracle_account": str(raw_account or "").strip(),
            "log_path": str(raw_path or "").strip(),
            "fatal_error_patterns": patterns,
        }
        oracle_account = str(raw_account or "").strip() or self.DEFAULT_ORACLE_ACCOUNT
        try:
            log_path = self._validate_absolute_path(raw_path, "log_path")
        except ValueError as exc:
            return self._failure("점검 설정 오류", str(exc), thresholds)
        if not patterns:
            return self._failure(
                "점검 설정 오류", "fatal_error_patterns 값이 비어 있습니다.", thresholds
            )
        command = "tail -100 " + shlex.quote(log_path)
        try:
            account_results = self._run_account_commands(
                oracle_account, [{"command": command, "timeout": 30}]
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
        if not stdout:
            return self._failure(
                "출력 파싱 실패",
                "최근 로그 출력이 비어 있습니다.",
                thresholds,
                metrics=metrics,
                stdout=stdout,
            )
        matches = []
        for line in stdout.splitlines():
            lowered = line.lower()
            found = [pattern for pattern in patterns if pattern.lower() in lowered]
            if found:
                matches.append({"line": line.strip(), "patterns": found})
        metrics.update(
            {
                "log_line_count": len(stdout.splitlines()),
                "fatal_match_count": len(matches),
                "fatal_matches": matches,
            }
        )
        if matches:
            reason = (
                "최근 100줄에서 설정된 치명적 오류 패턴이 %s건 확인되었습니다."
                % len(matches)
            )
            return self._failure(
                "치명적 오류 로그 발견",
                reason,
                thresholds,
                metrics=metrics,
                stdout=stdout,
            )
        reason = "최근 100줄에서 설정된 치명적 오류 패턴이 발견되지 않았습니다."
        return self.ok(metrics=metrics, message=reason)


CHECK_CLASS = Check
