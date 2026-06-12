# type_name

일상점검

# area_name

상태점검

# category_name

dbms

# application_type

oracle

# application

rocky

# inspection_code

DBMS-ORACLE-ROCKY-DB-5-1-PROCESSES

# is_required

필수

# inspection_name

프로세스 개수 점검

# inspection_content

DB에 설정된 최대 프로세스 개수 대비 DB 기동 후 현재시점까지 접속했던 세션 프로세스 개수에 대한 사용률 점검(초과 시 DB 접속 불가 및 서비스 지연)

# inspection_command

```bash
sqlplus -S /nolog <<EOF
CONNECT / AS SYSDBA
SELECT value AS "Max Processes", (SELECT COUNT(*) FROM v$session) AS "Current Sessions", ROUND((SELECT COUNT(*) FROM v$session) / value * 100, 2) AS "Usage %" FROM v$parameter WHERE name = 'processes';
EXIT;
EOF
```

# inspection_output

```text
[OS: Rocky 9.4] 추출된 결과입니다.
slunidb-dev241:/koem/oracle/diag/rdbms/unidev/UNIDEV/trace> sqlplus -S /nolog <<EOF
> CONNECT / AS SYSDBA
> SELECT
> value AS "Max Processes",
> (SELECT COUNT(*) FROM v\\$session) AS "Current Sessions",
> ROUND((SELECT COUNT(*) FROM v\\$session) / value * 100, 2) AS "Usage %"
> FROM v\\$parameter
> WHERE name = 'processes';
> EXIT;
> EOF

Max Processes
--------------------------------------------------------------------------------
Current Sessions    Usage %
---------------- ----------
1500
             168       11.2


---
```

# description

- `sqlplus`를 통해 시스템 리소스 한계치(Max Processes, SGA 설정 등)와 현재 사용량 통계를 조회합니다.

- **양호**: 사용량이 임계치 이내에서 안정적으로 관리됨
- **경고**: 프로세스, SGA 등의 사용량이 한계치에 임박하거나 초과함
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
