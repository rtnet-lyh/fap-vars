# -*- coding: utf-8 -*-

import re
from .common._base import BaseCheck

INSPECTION_NAME = "DB 시스템 로그 파일시스템 사용률"
DEFAULT_TARGET_MOUNT_PATTERNS = "/koem/oracle"
COMMAND = "df -h"


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = "paramiko"
    PARAMIKO_PROFILE = "linux"
    PARAMIKO_REUSE_SESSION = False
    DEFAULT_ORACLE_ACCOUNT = "oracle"

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

    def _parse_df(self, output):
        lines = [
            line.strip() for line in str(output or "").splitlines() if line.strip()
        ]
        header_index = -1
        for index, line in enumerate(lines):
            lowered = line.lower()
            if "filesystem" in lowered and "use%" in lowered and ("mounted" in lowered):
                header_index = index
                break
        if header_index < 0:
            return None
        entries = []
        for line in lines[header_index + 1 :]:
            parts = re.split("\\s+", line)
            if len(parts) < 6 or not re.match("^\\d+%$", parts[-2]):
                continue
            entries.append(
                {
                    "filesystem": " ".join(parts[:-5]),
                    "size": parts[-5],
                    "used": parts[-4],
                    "available": parts[-3],
                    "usage_percent": int(parts[-2].rstrip("%")),
                    "mount_point": parts[-1],
                }
            )
        return entries

    def run(self):
        raw_account = self.get_threshold_var(
            "oracle_account", default=self.DEFAULT_ORACLE_ACCOUNT, value_type="str"
        )
        max_usage = self.get_threshold_var(
            "max_usage_percent", default=80, value_type="int"
        )
        raw_patterns = self.get_threshold_var(
            "target_mount_patterns",
            default=DEFAULT_TARGET_MOUNT_PATTERNS,
            value_type="str",
        )
        patterns = self._parse_list(raw_patterns)
        thresholds = {
            "oracle_account": str(raw_account or "").strip(),
            "max_usage_percent": max_usage,
            "target_mount_patterns": patterns,
        }
        oracle_account = str(raw_account or "").strip() or self.DEFAULT_ORACLE_ACCOUNT
        if not patterns:
            return self._failure(
                "점검 설정 오류",
                "target_mount_patterns 값이 비어 있습니다.",
                thresholds,
            )
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
                message = str("df -h") + " 명령 실행에 실패했습니다."
            return self._failure(
                error,
                message,
                thresholds,
                metrics=metrics,
                stdout=stdout,
                stderr=stderr,
            )
        entries = self._parse_df(stdout)
        if entries is None:
            return self._failure(
                "출력 파싱 실패",
                "df -h 출력에서 Filesystem/Use%/Mounted 헤더를 찾지 못했습니다.",
                thresholds,
                metrics=metrics,
                stdout=stdout,
            )
        if not entries:
            return self._failure(
                "출력 파싱 실패",
                "df -h 출력에서 파일시스템 사용률 행을 해석하지 못했습니다.",
                thresholds,
                metrics=metrics,
                stdout=stdout,
            )
        targets = [
            entry
            for entry in entries
            if any(
                (
                    pattern.lower() in entry["mount_point"].lower()
                    for pattern in patterns
                )
            )
        ]
        if not targets:
            missing_metrics = dict(metrics)
            missing_metrics["parsed_mount_points"] = [
                entry["mount_point"] for entry in entries
            ]
            return self._failure(
                "대상 파일시스템 없음",
                "target_mount_patterns에 일치하는 mount point가 없습니다.",
                thresholds,
                metrics=missing_metrics,
                stdout=stdout,
            )
        highest = max(targets, key=lambda entry: entry["usage_percent"])
        exceeded = [entry for entry in targets if entry["usage_percent"] > max_usage]
        metrics.update(
            {
                "target_mount_count": len(targets),
                "target_mounts": targets,
                "max_usage_percent": highest["usage_percent"],
                "max_usage_mount_point": highest["mount_point"],
                "over_threshold_mounts": exceeded,
            }
        )
        if exceeded:
            reason = "파일시스템 사용률이 기준을 초과했습니다: " + ", ".join(
                (
                    "%s=%s%%" % (entry["mount_point"], entry["usage_percent"])
                    for entry in exceeded
                )
            )
            return self._failure(
                "파일시스템 사용률 임계치 초과",
                reason,
                thresholds,
                metrics=metrics,
                stdout=stdout,
            )
        reason = "대상 파일시스템 최대 사용률 %s%%가 기준 %s%% 이하입니다." % (
            highest["usage_percent"],
            max_usage,
        )
        return self.ok(metrics=metrics, message=reason)


CHECK_CLASS = Check
