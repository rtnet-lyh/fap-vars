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

DBMS-ORACLE-ROCKY-DB-3-2-OS-CPU

# is_required

필수

# inspection_name

물리적 CPU 사용률

# inspection_content

DB 기동중인 상태에서 물리적 CPU 사용률 상태가 적절한 수치를 유지하는지 점검

# inspection_command

```bash
ps -eo pid,comm,%cpu --sort=-%cpu | grep ora_ | grep -v grep | head -10
```

# inspection_output

```text
[OS: Rocky 9.4] 추출된 결과입니다.
slunidb-dev241:/home/oracle> ps -eo pid,comm,%cpu --sort=-%cpu | grep ora_ | grep -v grep | head -10
3229820 ora_vkrm_unidev  0.1
3229828 ora_dia0_unidev  0.1
 139563 ora_w002_unidev  0.0
 359607 ora_m004_unidev  0.0
 475615 ora_w005_unidev  0.0
 524302 ora_w009_unidev  0.0
 652248 ora_w004_unidev  0.0
 708294 ora_w001_unidev  0.0
 728381 ora_w00e_unidev  0.0
 811760 ora_m006_unidev  0.0




---
```

# description

- `ps` 명령을 통해 Oracle 관련 메인 프로세스, 메모리, CPU 사용률을 점검합니다.

- **양호**: 프로세스 상태가 정상이고 자원 사용률이 임계치 이하로 유지됨
- **경고**: 자원 사용률이 임계치를 초과하거나 비정상 상태, 프로세스가 구동되지 않음
- **확인 필요**: 명령어 오류 또는 수집 결과 포맷 불일치로 확인 불가

# thresholds

[
    {id: null, key: "oracle_account", value: "lyh", sortOrder: 0}
,
{id: null, key: "max_usage_percent", value: "80", sortOrder: 1}
]

# inspection_script

# -*- coding: utf-8 -*-

import re
from .common._base import BaseCheck

RESOURCE_KIND = "cpu"
INSPECTION_NAME = "Oracle 프로세스 CPU 사용률"
COMMAND = "ps -eo pid,comm,%cpu --sort=-%cpu | grep ora_ | grep -v grep | head -10"
PROCESS_PATTERN = re.compile("^\\s*(\\d+)\\s+(ora_\\S+)\\s+([0-9]+(?:\\.[0-9]+)?)\\s*$")


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

    def _parse_processes(self, output):
        processes = []
        for line in str(output or "").splitlines():
            match = PROCESS_PATTERN.match(line)
            if not match:
                continue
            item = {
                "pid": int(match.group(1)),
                "process": match.group(2),
                "usage_percent": float(match.group(3)),
            }
            if RESOURCE_KIND == "memory":
                item["rss_kb"] = int(match.group(4))
                item["vsz_kb"] = int(match.group(5))
            processes.append(item)
        return processes

    def run(self):
        raw_account = self.get_threshold_var(
            "oracle_account", default=self.DEFAULT_ORACLE_ACCOUNT, value_type="str"
        )
        max_usage = self.get_threshold_var(
            "max_usage_percent", default=80.0, value_type="float"
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
                message = str(INSPECTION_NAME) + " 명령 실행에 실패했습니다."
            return self._failure(
                error,
                message,
                thresholds,
                metrics=metrics,
                stdout=stdout,
                stderr=stderr,
            )
        processes = self._parse_processes(stdout)
        if not processes:
            return self._failure(
                "출력 파싱 실패",
                "Oracle 프로세스 자원 사용률 행을 해석하지 못했습니다.",
                thresholds,
                metrics=metrics,
                stdout=stdout,
            )
        ordered = sorted(
            processes, key=lambda item: item["usage_percent"], reverse=True
        )
        exceeded = [item for item in ordered if item["usage_percent"] > max_usage]
        metrics.update(
            {
                "process_count": len(processes),
                "max_usage_percent": ordered[0]["usage_percent"],
                "max_usage_process": ordered[0],
                "top_processes": ordered[:10],
                "over_threshold_processes": exceeded,
            }
        )
        if exceeded:
            message = "%s 최대 사용률 %.2f%%가 기준 %.2f%%를 초과했습니다." % (
                INSPECTION_NAME,
                ordered[0]["usage_percent"],
                max_usage,
            )
            return self._failure(
                "자원 사용률 임계치 초과",
                message,
                thresholds,
                metrics=metrics,
                stdout=stdout,
            )
        reason = "%s 최대 사용률 %.2f%%가 기준 %.2f%% 이하입니다." % (
            INSPECTION_NAME,
            ordered[0]["usage_percent"],
            max_usage,
        )
        return self.ok(metrics=metrics, message=reason)


CHECK_CLASS = Check
