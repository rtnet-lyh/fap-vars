# type_name

일상점검

# area_name

dbms

# category_name

상태점검

# application_type

oracle

# application

rocky

# inspection_code

DBMS-ORACLE-ROCKY-DB-8-1-RMAN-BACKUP

# is_required

필수

# inspection_name

DB 백업 상태 점검

# inspection_content

백업 형태(Begin/End, Rman, Exp 등), 날짜, 로그, 파일수 등을 점검하여 장애 시 완전 복구 가능 여부 점검

# inspection_command

```bash
rman TARGET / << EOF
LIST BACKUP SUMMARY;
EXIT;
EOF
```

# inspection_output

```text
[OS: Rocky 9.4] 추출된 결과입니다.
slunidb-dev241:/koem/oracle/diag/rdbms/unidev/UNIDEV/trace> rman TARGET / << EOF
> LIST BACKUP SUMMARY;
> EXIT;
> EOF

Recovery Manager: Release 19.0.0.0.0 - Production on Fri Jun 5 14:08:48 2026
Version 19.25.0.0.0

Copyright (c) 1982, 2019, Oracle and/or its affiliates.  All rights reserved.

connected to target database: UNIDEV (DBID=1665036402)

RMAN> LIST BACKUP SUMMARY;
using target database control file instead of recovery catalog
specification does not match any backup in the repository


RMAN> EXIT;

Recovery Manager complete.




---
```

# description

- `rman` 도구 등을 사용하여 백업 수행 결과 및 온라인 백업 가능 설정 등을 확인합니다.

- **양호**: 백업이 에러 없이 정상적으로 수행 및 완료됨
- **경고**: 백업 실패 이력 또는 오래된 백업만 존재
- **확인 필요**: 실행 에러 또는 백업 내역 확인 불가

# thresholds

[
    {id: null, key: "oracle_account", value: "lyh", sortOrder: 0}
,
{id: null, key: "max_backup_age_days", value: "7", sortOrder: 1}
,
{id: null, key: "failure_patterns", value: "specification does not match any backup|no backup|failed|failure", sortOrder: 2}
]

# inspection_script

# -*- coding: utf-8 -*-

from datetime import date
import re
from .common._base import BaseCheck

DEFAULT_FAILURE_PATTERNS = (
    "specification does not match any backup|no backup|failed|failure"
)
COMMAND = "rman TARGET / <<'EOF'\nLIST BACKUP SUMMARY;\nEXIT;\nEOF"
MONTHS = {
    "JAN": 1,
    "FEB": 2,
    "MAR": 3,
    "APR": 4,
    "MAY": 5,
    "JUN": 6,
    "JUL": 7,
    "AUG": 8,
    "SEP": 9,
    "OCT": 10,
    "NOV": 11,
    "DEC": 12,
}


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

    def _parse_completion_dates(self, output):
        dates = []
        for line in str(output or "").splitlines():
            match = re.match(
                "^\\s*\\d+\\s+\\S+\\s+\\S+\\s+\\S+\\s+\\S+\\s+(\\d{2})-([A-Za-z]{3})-(\\d{2,4})\\b",
                line,
            )
            if not match:
                continue
            day = int(match.group(1))
            month = MONTHS.get(match.group(2).upper())
            year = int(match.group(3))
            if year < 100:
                year += 2000 if year < 70 else 1900
            if month:
                dates.append(date(year, month, day))
        return dates

    def run(self):
        raw_account = self.get_threshold_var(
            "oracle_account", default=self.DEFAULT_ORACLE_ACCOUNT, value_type="str"
        )
        max_age_days = self.get_threshold_var(
            "max_backup_age_days", default=7, value_type="int"
        )
        raw_patterns = self.get_threshold_var(
            "failure_patterns", default=DEFAULT_FAILURE_PATTERNS, value_type="str"
        )
        failure_patterns = self._parse_list(raw_patterns)
        thresholds = {
            "oracle_account": str(raw_account or "").strip(),
            "max_backup_age_days": max_age_days,
            "failure_patterns": failure_patterns,
        }
        oracle_account = str(raw_account or "").strip() or self.DEFAULT_ORACLE_ACCOUNT
        if max_age_days < 0 or not failure_patterns:
            return self._failure(
                "점검 설정 오류",
                "max_backup_age_days 또는 failure_patterns 설정이 올바르지 않습니다.",
                thresholds,
            )
        try:
            account_results = self._run_account_commands(
                oracle_account, [{"command": COMMAND, "timeout": 60}]
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
                message = str("RMAN 백업 요약 조회") + " 명령 실행에 실패했습니다."
            return self._failure(
                error,
                message,
                thresholds,
                metrics=metrics,
                stdout=stdout,
                stderr=stderr,
            )
        lowered = stdout.lower()
        matched_failures = [
            pattern for pattern in failure_patterns if pattern.lower() in lowered
        ]
        rman_errors = sorted(set(re.findall("\\b(?:RMAN|ORA)-\\d+\\b", stdout, re.I)))
        metrics.update(
            {
                "matched_failure_patterns": matched_failures,
                "rman_error_codes": rman_errors,
            }
        )
        if matched_failures or rman_errors:
            reason = "RMAN 백업 없음 또는 실패 근거가 확인되었습니다."
            return self._failure(
                "RMAN 백업 정책 위반",
                reason,
                thresholds,
                metrics=metrics,
                stdout=stdout,
            )
        completion_dates = self._parse_completion_dates(stdout)
        if not completion_dates:
            return self._failure(
                "출력 파싱 실패",
                "RMAN LIST BACKUP SUMMARY에서 정상 백업 완료일을 해석하지 못했습니다.",
                thresholds,
                metrics=metrics,
                stdout=stdout,
            )
        latest = max(completion_dates)
        age_days = (date.today() - latest).days
        metrics.update(
            {
                "backup_count": len(completion_dates),
                "latest_backup_date": latest.isoformat(),
                "backup_age_days": age_days,
            }
        )
        if age_days > max_age_days:
            reason = "최근 정상 백업이 %s일 경과하여 기준 %s일을 초과했습니다." % (
                age_days,
                max_age_days,
            )
            return self._failure(
                "RMAN 최근 백업 기준 초과",
                reason,
                thresholds,
                metrics=metrics,
                stdout=stdout,
            )
        reason = "최근 정상 백업이 %s일 이내에 존재합니다." % max_age_days
        return self.ok(metrics=metrics, message=reason)


CHECK_CLASS = Check
