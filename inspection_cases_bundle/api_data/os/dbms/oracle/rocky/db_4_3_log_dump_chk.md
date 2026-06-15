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


DB-OR-RKY-009

# is_required

필수

# inspection_name

Dump파일 생성 여부 확인(DB 오류 발생시 생성)

# inspection_content

DB가 문제 발생시 생성되는 trace(dump)파일로 원인 분석에 주로 사용되며 원인 파일을 위한 파일 점검

# inspection_command

```bash
ls -ltr /koem/oracle/diag/rdbms/unidev/UNIDEV/trace/*.trc 2>/dev/null | tail -5
```

# inspection_output

```text
[OS: Rocky 9.4] 추출된 결과입니다.
slunidb-dev241:> ls -ltr /koem/oracle/diag/rdbms/unidev/UNIDEV/trace/*.trc 2>/dev/null | tail -5
-rw-r----- 1 oracle dba     1414  6월  3 22:00 /koem/oracle/diag/rdbms/unidev/UNIDEV/trace/UNIDEV_j002_3673719.trc
-rw-r----- 1 oracle dba    30967  6월  4 22:00 /koem/oracle/diag/rdbms/unidev/UNIDEV/trace/UNIDEV_cjq0_3234419.trc
-rw-r----- 1 oracle dba     1414  6월  4 22:00 /koem/oracle/diag/rdbms/unidev/UNIDEV/trace/UNIDEV_j002_3875968.trc
-rw-r----- 1 oracle dba  1375409  6월  5 13:05 /koem/oracle/diag/rdbms/unidev/UNIDEV/trace/UNIDEV_vkrm_3229820.trc
-rw-r----- 1 oracle dba 14114554  6월  5 13:57 /koem/oracle/diag/rdbms/unidev/UNIDEV/trace/UNIDEV_dbrm_3229816.trc




---
```

# description

- `alert.log` 및 `listener.log`, `*.trc` 등의 파일 내용을 점검하여 DB와 리스너에서 발생한 오류나 경고를 파악합니다.

- **양호**: 시스템 장애를 유발할 수 있는 치명적인 에러 로그가 없음
- **경고**: 서비스 지연이나 장애를 일으키는 에러 다수 발생
- **확인 필요**: 파일 경로 오류 등으로 로그 확인 불가

# thresholds

[
    {id: null, key: "oracle_account", value: "lyh", sortOrder: 0}
,
{id: null, key: "trace_path", value: "/koem/oracle/diag/rdbms/unidev/UNIDEV/trace", sortOrder: 1}
,
{id: null, key: "recent_file_count", value: "5", sortOrder: 2}
]

# inspection_script

# -*- coding: utf-8 -*-

import re
import shlex
from .common._base import BaseCheck

DEFAULT_TRACE_PATH = "/koem/oracle/diag/rdbms/unidev/UNIDEV/trace"


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

    def _failure(
        self, error, message, thresholds, metrics=None, stdout=None, stderr=None
    ):
        return self.fail(error, metrics=metrics or {}, message=message)

    def run(self):
        raw_account = self.get_threshold_var(
            "oracle_account", default=self.DEFAULT_ORACLE_ACCOUNT, value_type="str"
        )
        raw_path = self.get_threshold_var(
            "trace_path", default=DEFAULT_TRACE_PATH, value_type="str"
        )
        recent_count = self.get_threshold_var(
            "recent_file_count", default=5, value_type="int"
        )
        thresholds = {
            "oracle_account": str(raw_account or "").strip(),
            "trace_path": str(raw_path or "").strip(),
            "recent_file_count": recent_count,
        }
        oracle_account = str(raw_account or "").strip() or self.DEFAULT_ORACLE_ACCOUNT
        try:
            trace_path = self._validate_absolute_path(raw_path, "trace_path")
        except ValueError as exc:
            return self._failure("점검 설정 오류", str(exc), thresholds)
        if recent_count <= 0:
            return self._failure(
                "점검 설정 오류", "recent_file_count는 1 이상이어야 합니다.", thresholds
            )
        command = "ls -ltr %s/*.trc 2>/dev/null | tail -%s" % (
            shlex.quote(trace_path),
            recent_count,
        )
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
                message = str("Oracle trace 파일 조회") + " 명령 실행에 실패했습니다."
            return self._failure(
                error,
                message,
                thresholds,
                metrics=metrics,
                stdout=stdout,
                stderr=stderr,
            )
        trace_files = []
        for line in stdout.splitlines():
            stripped = line.strip()
            if not stripped.startswith("-") or ".trc" not in stripped:
                continue
            trace_files.append({"path": stripped.split()[-1], "listing": stripped})
        metrics.update(
            {"trace_file_count": len(trace_files), "trace_files": trace_files}
        )
        if trace_files:
            reason = "최근 trace 파일 %s건이 있어 수동 원인 분석이 필요합니다." % len(
                trace_files
            )
            return self.warn(metrics=metrics, message=reason)
        if stdout.strip():
            return self._failure(
                "출력 파싱 실패",
                "trace 파일 목록 출력을 해석하지 못했습니다.",
                thresholds,
                metrics=metrics,
                stdout=stdout,
            )
        reason = "최근 trace 파일이 발견되지 않았습니다."
        return self.ok(metrics=metrics, message=reason)


CHECK_CLASS = Check
