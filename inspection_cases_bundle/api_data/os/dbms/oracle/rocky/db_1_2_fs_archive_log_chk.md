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


DB-OR-RKY-002

# is_required

필수

# inspection_name

아카이브(데이터변경) 로그 파일시스템

# inspection_content

DB 데이터 변경 사항을 기록하는 아카이브 로그 파일 물리적인 저장 공간 사용률(Full 시 서비스 불가)

# inspection_command

```bash
df -h
```

# inspection_output

```text
[OS: Rocky 9.4] 추출된 결과입니다.
slunidb-dev241:/home/oracle> df -h
Filesystem           Size  Used Avail Use% Mounted on
devtmpfs             4.0M     0  4.0M   0% /dev
tmpfs                 32G     0   32G   0% /dev/shm
tmpfs                 13G  1.3G   12G  10% /run
/dev/mapper/rl-root  200G   39G  162G  20% /
/dev/md126p2         960M  298M  663M  32% /boot
/dev/mapper/rl-home  617G  4.4G  612G   1% /home
/dev/mapper/vg0-lv0  196G   42G  145G  23% /koem/oracle
/dev/mapper/vg2-lv1  1.5T  476G  970G  33% /koem/oradata/data
/dev/mapper/vg1-lv0  295G  6.7G  273G   3% /koem/oradata/arch
/dev/md126p1         599M  7.1M  592M   2% /boot/efi
tmpfs                6.3G  104K  6.3G   1% /run/user/0
/dev/loop0            11G   11G     0 100% /mnt
tmpfs                6.3G   36K  6.3G   1% /run/user/1000



---
```

# description

- `df -h` 명령을 통해 DB 엔진, 아카이브 로그, DB 시스템 로그가 위치한 파일시스템의 사용률을 확인합니다.

- **양호**: 파일시스템 사용률이 임계치 이하로 유지됨
- **경고**: 파일시스템 사용률이 임계치를 초과하여 디스크 고갈 위험이 있음
- **확인 필요**: 명령어 실행 실패, 수집된 출력 결과와 포맷이 다르거나 확인이 불가능한 상태

# thresholds

[
    {id: null, key: "oracle_account", value: "lyh", sortOrder: 0}
,
{id: null, key: "max_usage_percent", value: "80", sortOrder: 1}
,
{id: null, key: "target_mount_patterns", value: "/koem/oradata/arch", sortOrder: 2}
]

# inspection_script

# -*- coding: utf-8 -*-

import re
from .common._base import BaseCheck

INSPECTION_NAME = "아카이브 로그 파일시스템 사용률"
DEFAULT_TARGET_MOUNT_PATTERNS = "/koem/oradata/arch"
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
