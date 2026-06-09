# -*- coding: utf-8 -*-

import re
from .common._base import BaseCheck

COMMAND = "sqlplus -S /nolog <<'EOF'\nCONNECT / AS SYSDBA\nSELECT GROUP#, MEMBERS, BYTES/1024/1024 AS SIZE_MB, STATUS FROM V$LOG;\nEXIT;\nEOF"


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

    def _parse_groups(self, output):
        groups = []
        for line in str(output or "").splitlines():
            match = re.match(
                "^\\s*(\\d+)\\s+(\\d+)\\s+([0-9]+(?:\\.[0-9]+)?)\\s+(\\S+)\\s*$", line
            )
            if not match:
                continue
            groups.append(
                {
                    "group": int(match.group(1)),
                    "members": int(match.group(2)),
                    "size_mb": float(match.group(3)),
                    "status": match.group(4),
                }
            )
        return groups

    def run(self):
        raw_account = self.get_threshold_var(
            "oracle_account", default=self.DEFAULT_ORACLE_ACCOUNT, value_type="str"
        )
        max_size_mb = self.get_threshold_var(
            "max_redo_size_mb", default=1024.0, value_type="float"
        )
        thresholds = {
            "oracle_account": str(raw_account or "").strip(),
            "max_redo_size_mb": max_size_mb,
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
                message = str("Redo log 크기 조회") + " 명령 실행에 실패했습니다."
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
        groups = self._parse_groups(stdout)
        if not groups:
            return self._failure(
                "출력 파싱 실패",
                "V$LOG 그룹별 크기 결과를 해석하지 못했습니다.",
                thresholds,
                metrics=metrics,
                stdout=stdout,
            )
        ordered = sorted(groups, key=lambda item: item["size_mb"], reverse=True)
        exceeded = [item for item in ordered if item["size_mb"] > max_size_mb]
        metrics.update(
            {
                "redo_group_count": len(groups),
                "max_redo_size_mb": ordered[0]["size_mb"],
                "redo_groups": sorted(groups, key=lambda item: item["group"]),
                "over_threshold_groups": exceeded,
            }
        )
        if exceeded:
            reason = "Redo log 그룹 크기가 기준을 초과했습니다: " + ", ".join(
                (
                    "group%s=%.2fMB" % (item["group"], item["size_mb"])
                    for item in exceeded
                )
            )
            return self._failure(
                "Redo log 크기 기준 초과",
                reason,
                thresholds,
                metrics=metrics,
                stdout=stdout,
            )
        reason = "최대 Redo log 크기 %.2fMB가 기준 %.2fMB 이하입니다." % (
            ordered[0]["size_mb"],
            max_size_mb,
        )
        return self.ok(metrics=metrics, message=reason)


CHECK_CLASS = Check
