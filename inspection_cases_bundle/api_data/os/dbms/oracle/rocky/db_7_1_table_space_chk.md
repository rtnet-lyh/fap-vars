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


DB-OR-RKY-012

# is_required

필수

# inspection_name

테이블 스페이스 사용률 점검

# inspection_content

DB 데이터가 저장되는 테이블 스페이스 영역의 사용률이 90% 이상을 사용할 경우 테이블 스페이스 공간 확보 대비

# inspection_command

```bash
sqlplus -S /nolog <<EOF
CONNECT / AS SYSDBA
select * from DBA_TABLESPACE_USAGE_METRICS;
EXIT;
EOF
```

# inspection_output

```text
[OS: Rocky 9.4] 추출된 결과입니다.
slunidb-dev241:/koem/oracle/diag/rdbms/unidev/UNIDEV/trace> sqlplus -S /nolog <<EOF
CONNECT / AS SYSDBA
select * from DBA_TABLESPACE_USAGE_METRICS;
EXIT;
EOF

TABLESPACE_NAME                USED_SPACE TABLESPACE_SIZE USED_PERCENT
------------------------------ ---------- --------------- ------------
ATFW                               196736         3932160   5.00325521
HDATA_1_GW8                       1318960         3932160   33.5428874
HDATA_2_GW8                       2121872         3932160   53.9619954
HDATA_3_GW8                         10768         3932160   .273844401
HDATA_4_GW8                        272000         3932160   6.91731771
HINDEX_1_GW8                        13184         3932160   .335286458
HINDEX_2_GW8                      3215936         7864320   40.8927409
HINDEX_3_GW8                        52992         3932160   1.34765625
HQDB_GW8                           819208         3932160   20.8335368
HQDB_X_GW8                         198288         3932160   5.04272461
SYSAUX                             128968         4194302    3.0748382

TABLESPACE_NAME                USED_SPACE TABLESPACE_SIZE USED_PERCENT
------------------------------ ---------- --------------- ------------
SYSTEM                             147264         4194302   3.51104904
TEMP                                    0         4194176            0
TSINTRA_1_GW8                     1024216         3932160   26.0471598
TSINTRA_2_GW8                      135112         3932160   3.43607585
TSINTRA_3_GW8                       76928         3932160   1.95638021
TSINTRA_4X_GW8                     272784         3932160   6.93725586
TSINTRA_4_GW8                      628864         3932160   15.9928385
TSINTRA_5X_GW8                        128         3932160   .003255208
TSINTRA_5_GW8                         128         3932160   .003255208
TSINTRA_X_GW8                      200608         3932160   5.10172526
UNDOTBS1                             1544         4194302   .036811846

TABLESPACE_NAME                USED_SPACE TABLESPACE_SIZE USED_PERCENT
------------------------------ ---------- --------------- ------------
USERS                                 344         4194302   .008201603

23 rows selected.


---
```

# description

- 딕셔너리(`DBA_TABLESPACE_USAGE_METRICS`, `V$LOG` 등)를 조회하여 테이블 스페이스 사용률, 리두 로그 파일 사이즈 등 용량을 점검합니다.

- **양호**: 사용률이 한계치 이하로 여유가 있음
- **경고**: 한계치 초과 또는 자동 확장이 불가한 상태로 용량 임박
- **확인 필요**: 쿼리 실패 또는 수집 결과 포맷 불일치

# thresholds

[
    {id: null, key: "oracle_account", value: "lyh", sortOrder: 0}
,
{id: null, key: "max_usage_percent", value: "90", sortOrder: 1}
]

# inspection_script

# -*- coding: utf-8 -*-

import re
from .common._base import BaseCheck

COMMAND = "sqlplus -S /nolog <<'EOF'\nCONNECT / AS SYSDBA\nselect * from DBA_TABLESPACE_USAGE_METRICS;\nEXIT;\nEOF"


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

    def _parse_tablespaces(self, output):
        entries = []
        for line in str(output or "").splitlines():
            match = re.match(
                "^\\s*(\\S+)\\s+(\\d+)\\s+(\\d+)\\s+([0-9]*\\.?[0-9]+)\\s*$", line
            )
            if not match or match.group(1).upper() == "TABLESPACE_NAME":
                continue
            entries.append(
                {
                    "tablespace_name": match.group(1),
                    "used_space": int(match.group(2)),
                    "tablespace_size": int(match.group(3)),
                    "used_percent": float(match.group(4)),
                }
            )
        return entries

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
                    str("테이블 스페이스 사용률 조회") + " 명령 실행에 실패했습니다."
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
        entries = self._parse_tablespaces(stdout)
        if not entries:
            return self._failure(
                "출력 파싱 실패",
                "DBA_TABLESPACE_USAGE_METRICS 결과 행을 해석하지 못했습니다.",
                thresholds,
                metrics=metrics,
                stdout=stdout,
            )
        ordered = sorted(entries, key=lambda item: item["used_percent"], reverse=True)
        exceeded = [item for item in ordered if item["used_percent"] > max_usage]
        metrics.update(
            {
                "tablespace_count": len(entries),
                "max_used_percent": ordered[0]["used_percent"],
                "max_used_tablespace": ordered[0]["tablespace_name"],
                "tablespaces": ordered,
                "over_threshold_tablespaces": exceeded,
            }
        )
        if exceeded:
            reason = "테이블 스페이스 사용률이 기준을 초과했습니다: " + ", ".join(
                (
                    "%s=%.2f%%" % (item["tablespace_name"], item["used_percent"])
                    for item in exceeded
                )
            )
            return self._failure(
                "테이블 스페이스 사용률 임계치 초과",
                reason,
                thresholds,
                metrics=metrics,
                stdout=stdout,
            )
        reason = "최대 테이블 스페이스 사용률 %.2f%%가 기준 %.2f%% 이하입니다." % (
            ordered[0]["used_percent"],
            max_usage,
        )
        return self.ok(metrics=metrics, message=reason)


CHECK_CLASS = Check
