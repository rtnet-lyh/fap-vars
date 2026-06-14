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

DBMS-ORACLE-ROCKY-DB-2-3-DB-ACCESS

# is_required

필수

# inspection_name

DB 접속 상태 점검

# inspection_content

DB가 기동되어 있으나 실제 이상없이 DB가 접속 가능하는지 점검(SQL 커맨드 모드로 접근하여 명령어 수행 상태 정상 점검)

# inspection_command

```bash
sqlplus -S /nolog <<EOF
CONNECT / AS SYSDBA
SELECT 'DB is accessible' AS STATUS FROM dual;
EXIT;
EOF
```

# inspection_output

```text
[OS: Rocky 9.4] 추출된 결과입니다.
slunidb-dev241:/home/oracle> sqlplus -S /nolog <<EOF
> CONNECT / AS SYSDBA
> SELECT 'DB is accessible' AS STATUS FROM dual;
> EXIT;
> EOF

STATUS
----------------
DB is accessible

slunidb-dev241:/home/oracle>




---
```

# description

- 접속(`sqlplus`)을 통해 데이터베이스의 오픈 상태와 접근 가능 여부를 확인합니다.

- **양호**: DB 접속 및 쿼리가 정상 수행됨
- **경고**: DB 연결 실패 혹은 에러 반환
- **확인 필요**: 수집된 쿼리 결과 포맷 오류 또는 확인 불가

# thresholds

[
    {id: null, key: "oracle_account", value: "lyh", sortOrder: 0}
,
{id: null, key: "access_marker", value: "DB is accessible", sortOrder: 1}
]

# inspection_script

# -*- coding: utf-8 -*-

import re
from .common._base import BaseCheck

COMMAND = "sqlplus -S /nolog <<'EOF'\nCONNECT / AS SYSDBA\nSELECT 'DB is accessible' AS STATUS FROM dual;\nEXIT;\nEOF"


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

    def run(self):
        raw_account = self.get_threshold_var(
            "oracle_account", default=self.DEFAULT_ORACLE_ACCOUNT, value_type="str"
        )
        access_marker = str(
            self.get_threshold_var(
                "access_marker", default="DB is accessible", value_type="str"
            )
            or ""
        ).strip()
        thresholds = {
            "oracle_account": str(raw_account or "").strip(),
            "access_marker": access_marker,
        }
        oracle_account = str(raw_account or "").strip() or self.DEFAULT_ORACLE_ACCOUNT
        if not access_marker:
            return self._failure(
                "점검 설정 오류", "access_marker 값이 비어 있습니다.", thresholds
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
                message = str("sqlplus DB 접속 확인") + " 명령 실행에 실패했습니다."
            return self._failure(
                error,
                message,
                thresholds,
                metrics=metrics,
                stdout=stdout,
                stderr=stderr,
            )
        sql_errors = self._sql_errors(stdout)
        marker_found = access_marker.lower() in stdout.lower()
        metrics.update(
            {"access_marker_found": marker_found, "sqlplus_error_codes": sql_errors}
        )
        if sql_errors:
            message = "SQLPlus 오류 코드가 확인되었습니다: " + ", ".join(sql_errors)
            return self._failure(
                "DB 접속 정책 위반", message, thresholds, metrics=metrics, stdout=stdout
            )
        if not marker_found:
            return self._failure(
                "출력 파싱 실패",
                "DB 접속 확인 문자열을 SQLPlus 출력에서 찾지 못했습니다.",
                thresholds,
                metrics=metrics,
                stdout=stdout,
            )
        reason = "SQLPlus 오류 코드가 없고 DB 접근 확인 문자열이 존재합니다."
        return self.ok(metrics=metrics, message=reason)


CHECK_CLASS = Check
