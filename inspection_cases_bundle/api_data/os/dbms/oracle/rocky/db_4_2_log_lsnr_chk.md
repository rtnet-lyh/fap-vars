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


DB-OR-RKY-008

# is_required

필수

# inspection_name

리스너(DB 서비스 연결) 로그 파일 점검

# inspection_content

리스너를 통해 DB에 접근하는 클라이언트에 대한 로그 파일로 세션 접속(WAS와 DB간)에 문제가 있는지 점검

# inspection_command

```bash
grep -i -E 'connection refused|timeout|TNS listener stopped|warning|TNS-12541|TNS-12514|TNS-12170' /koem/oracle/diag/tnslsnr/slunidb-dev241/listener/trace/listener.log || echo '에러로그없음'
```

# inspection_output

```text
[OS: Rocky 9.4] 추출된 결과입니다.
slunidb-dev241:/koem> grep -i -E 'connection refused|timeout|TNS listener stopped|warning|TNS-12541|TNS-12514|TNS-12170' /koem/oracle/diag/tnslsnr/slunidb-dev241/listener/trace/listener.log || echo '에러로그없음'
에러로그없음




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
{id: null, key: "listener_log_path", value: "/koem/oracle/diag/tnslsnr/slunidb-dev241/listener/trace/listener.log", sortOrder: 1}
,
{id: null, key: "fatal_error_patterns", value: "connection refused|timeout|TNS listener stopped|warning|TNS-12541|TNS-12514|TNS-12170", sortOrder: 2}
]

# inspection_script

# -*- coding: utf-8 -*-

import re
import shlex
from .common._base import BaseCheck

DEFAULT_LISTENER_LOG_PATH = (
    "/koem/oracle/diag/tnslsnr/slunidb-dev241/listener/trace/listener.log"
)
DEFAULT_FATAL_PATTERNS = "connection refused|timeout|TNS listener stopped|warning|TNS-12541|TNS-12514|TNS-12170"


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

    NO_ERROR_MARKER = "에러로그없음"

    def run(self):
        raw_account = self.get_threshold_var(
            "oracle_account", default=self.DEFAULT_ORACLE_ACCOUNT, value_type="str"
        )
        raw_path = self.get_threshold_var(
            "listener_log_path", default=DEFAULT_LISTENER_LOG_PATH, value_type="str"
        )
        raw_patterns = self.get_threshold_var(
            "fatal_error_patterns", default=DEFAULT_FATAL_PATTERNS, value_type="str"
        )
        patterns = self._parse_list(raw_patterns)
        thresholds = {
            "oracle_account": str(raw_account or "").strip(),
            "listener_log_path": str(raw_path or "").strip(),
            "fatal_error_patterns": patterns,
        }
        oracle_account = str(raw_account or "").strip() or self.DEFAULT_ORACLE_ACCOUNT
        try:
            log_path = self._validate_absolute_path(raw_path, "listener_log_path")
        except ValueError as exc:
            return self._failure("점검 설정 오류", str(exc), thresholds)
        if not patterns:
            return self._failure(
                "점검 설정 오류", "fatal_error_patterns 값이 비어 있습니다.", thresholds
            )
        expression = "|".join(patterns)
        command = "grep -i -E %s %s || echo %s" % (
            shlex.quote(expression),
            shlex.quote(log_path),
            shlex.quote(self.NO_ERROR_MARKER),
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
                message = str("리스너 로그 점검") + " 명령 실행에 실패했습니다."
            return self._failure(
                error,
                message,
                thresholds,
                metrics=metrics,
                stdout=stdout,
                stderr=stderr,
            )
        lines = [
            line.strip()
            for line in stdout.splitlines()
            if line.strip() and self.NO_ERROR_MARKER not in line
        ]
        matches = [
            line
            for line in lines
            if any((pattern.lower() in line.lower() for pattern in patterns))
        ]
        metrics.update(
            {
                "no_error_marker_found": self.NO_ERROR_MARKER in stdout,
                "fatal_match_count": len(matches),
                "fatal_log_lines": matches,
            }
        )
        if matches:
            reason = "리스너 로그에서 접속 오류 패턴이 %s건 확인되었습니다." % len(
                matches
            )
            return self._failure(
                "리스너 오류 로그 발견",
                reason,
                thresholds,
                metrics=metrics,
                stdout=stdout,
            )
        if self.NO_ERROR_MARKER not in stdout:
            return self._failure(
                "출력 파싱 실패",
                "리스너 로그 점검 결과에서 오류 행 또는 정상 확인 문자열을 찾지 못했습니다.",
                thresholds,
                metrics=metrics,
                stdout=stdout,
            )
        reason = "리스너 로그에서 설정된 접속 오류 패턴이 발견되지 않았습니다."
        return self.ok(metrics=metrics, message=reason)


CHECK_CLASS = Check
