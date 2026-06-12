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

DBMS-ORACLE-ROCKY-DB-4-1-DB-LOG

# is_required

필수

# inspection_name

DB 로그 파일 점검

# inspection_content

에러 코드(기동 및 정지, 테이블스 페이스 부족 에러, 백업 정상 유무, 데이터 파일 손상, Dead Lock 상태) 를 점검

# inspection_command

```bash
tail -100 /koem/oracle/diag/rdbms/unidev/UNIDEV/trace/alert_UNIDEV.log
```

# inspection_output

```text
[OS: Rocky 9.4] 추출된 결과입니다.
slunidb-dev241:/koem/oracle/diag/rdbms/unidev/UNIDEV/trace> tail -100 /koem/oracle/diag/rdbms/unidev/UNIDEV/trace/alert_UNIDEV.log
ORA-12012: error on auto execute of job "SYS"."ORA$AT_SQ_SQL_SW_3509"
ORA-38153: Software edition is incompatible with SQL plan management.
ORA-06512: at "SYS.DBMS_SPM_INTERNAL", line 6420
ORA-06512: at "SYS.DBMS_SPM", line 2840
ORA-06512: at line 34
2026-05-31T06:00:04.320016+09:00
TABLE SYS.WRI$_OPTSTAT_HISTHEAD_HISTORY: ADDED INTERVAL PARTITION SYS_P2393 (46172) VALUES LESS THAN (TO_DATE(' 2026-06-01 00:00:00', 'SYYYY-MM-DD HH24:MI:SS', 'NLS_CALENDAR=GREGORIAN'))
TABLE SYS.WRI$_OPTSTAT_HISTGRM_HISTORY: ADDED INTERVAL PARTITION SYS_P2396 (46172) VALUES LESS THAN (TO_DATE(' 2026-06-01 00:00:00', 'SYYYY-MM-DD HH24:MI:SS', 'NLS_CALENDAR=GREGORIAN'))
2026-05-31T10:09:03.894822+09:00
Errors in file /koem/oracle/diag/rdbms/unidev/UNIDEV/trace/UNIDEV_j002_2967433.trc:
ORA-12012: 작업 "SYS"."ORA$AT_SQ_SQL_SW_3512"의 자동 실행중 오류 발생
ORA-38153: 소프트웨어 에디션이 SQL 계획 관리와 호환되지 않습니다.
ORA-06512: "SYS.DBMS_SPM_INTERNAL",  6420행
ORA-06512: "SYS.DBMS_SPM",  2840행
ORA-06512:  34행
2026-05-31T10:09:06.647260+09:00
Thread 1 cannot allocate new log, sequence 141
Private strand flush not complete
  Current log# 2 seq# 140 mem# 0: /koem/oradata/redo/redo02.log
2026-05-31T10:09:09.677464+09:00
Thread 1 advanced to log sequence 141 (LGWR switch),  current SCN: 41990311310295
  Current log# 3 seq# 141 mem# 0: /koem/oradata/redo/redo03.log
2026-05-31T14:09:44.576669+09:00
Errors in file /koem/oracle/diag/rdbms/unidev/UNIDEV/trace/UNIDEV_j002_3000997.trc:
ORA-12012: 작업 "SYS"."ORA$AT_SQ_SQL_SW_3515"의 자동 실행중 오류 발생
ORA-38153: 소프트웨어 에디션이 SQL 계획 관리와 호환되지 않습니다.
ORA-06512: "SYS.DBMS_SPM_INTERNAL",  6420행
ORA-06512: "SYS.DBMS_SPM",  2840행
ORA-06512:  34행
2026-05-31T18:10:25.412900+09:00
Errors in file /koem/oracle/diag/rdbms/unidev/UNIDEV/trace/UNIDEV_j002_3034709.trc:
ORA-12012: 작업 "SYS"."ORA$AT_SQ_SQL_SW_3518"의 자동 실행중 오류 발생
ORA-38153: 소프트웨어 에디션이 SQL 계획 관리와 호환되지 않습니다.
ORA-06512: "SYS.DBMS_SPM_INTERNAL",  6420행
ORA-06512: "SYS.DBMS_SPM",  2840행
ORA-06512:  34행
2026-05-31T22:11:06.322727+09:00
Errors in file /koem/oracle/diag/rdbms/unidev/UNIDEV/trace/UNIDEV_j002_3068300.trc:
ORA-12012: 작업 "SYS"."ORA$AT_SQ_SQL_SW_3521"의 자동 실행중 오류 발생
ORA-38153: 소프트웨어 에디션이 SQL 계획 관리와 호환되지 않습니다.
ORA-06512: "SYS.DBMS_SPM_INTERNAL",  6420행
ORA-06512: "SYS.DBMS_SPM",  2840행
ORA-06512:  34행
2026-06-01T22:00:02.175674+09:00
Errors in file /koem/oracle/diag/rdbms/unidev/UNIDEV/trace/UNIDEV_j002_3269415.trc:
ORA-12012: 작업 "SYS"."ORA$AT_SQ_SQL_SW_3524"의 자동 실행중 오류 발생
ORA-38153: 소프트웨어 에디션이 SQL 계획 관리와 호환되지 않습니다.
ORA-06512: "SYS.DBMS_SPM_INTERNAL",  6420행
ORA-06512: "SYS.DBMS_SPM",  2840행
ORA-06512:  34행
2026-06-01T22:00:04.434780+09:00
TABLE SYS.WRI$_OPTSTAT_HISTHEAD_HISTORY: ADDED INTERVAL PARTITION SYS_P2397 (46173) VALUES LESS THAN (TO_DATE(' 2026-06-02 00:00:00', 'SYYYY-MM-DD HH24:MI:SS', 'NLS_CALENDAR=GREGORIAN'))
TABLE SYS.WRI$_OPTSTAT_HISTGRM_HISTORY: ADDED INTERVAL PARTITION SYS_P2400 (46173) VALUES LESS THAN (TO_DATE(' 2026-06-02 00:00:00', 'SYYYY-MM-DD HH24:MI:SS', 'NLS_CALENDAR=GREGORIAN'))
2026-06-01T22:00:14.187476+09:00
Thread 1 cannot allocate new log, sequence 142
Private strand flush not complete
  Current log# 3 seq# 141 mem# 0: /koem/oradata/redo/redo03.log
2026-06-01T22:00:17.197439+09:00
Thread 1 advanced to log sequence 142 (LGWR switch),  current SCN: 41990311419860
  Current log# 1 seq# 142 mem# 0: /koem/oradata/redo/redo01.log
2026-06-02T22:00:02.175637+09:00
Errors in file /koem/oracle/diag/rdbms/unidev/UNIDEV/trace/UNIDEV_j002_3471560.trc:
ORA-12012: 작업 "SYS"."ORA$AT_SQ_SQL_SW_3527"의 자동 실행중 오류 발생
ORA-38153: 소프트웨어 에디션이 SQL 계획 관리와 호환되지 않습니다.
ORA-06512: "SYS.DBMS_SPM_INTERNAL",  6420행
ORA-06512: "SYS.DBMS_SPM",  2840행
ORA-06512:  34행
2026-06-02T22:00:02.684575+09:00
TABLE SYS.WRI$_OPTSTAT_HISTHEAD_HISTORY: ADDED INTERVAL PARTITION SYS_P2401 (46174) VALUES LESS THAN (TO_DATE(' 2026-06-03 00:00:00', 'SYYYY-MM-DD HH24:MI:SS', 'NLS_CALENDAR=GREGORIAN'))
TABLE SYS.WRI$_OPTSTAT_HISTGRM_HISTORY: ADDED INTERVAL PARTITION SYS_P2404 (46174) VALUES LESS THAN (TO_DATE(' 2026-06-03 00:00:00', 'SYYYY-MM-DD HH24:MI:SS', 'NLS_CALENDAR=GREGORIAN'))
2026-06-03T10:32:22.829726+09:00
Thread 1 advanced to log sequence 143 (LGWR switch),  current SCN: 41990311529320
  Current log# 2 seq# 143 mem# 0: /koem/oradata/redo/redo02.log
2026-06-03T22:00:02.300554+09:00
Errors in file /koem/oracle/diag/rdbms/unidev/UNIDEV/trace/UNIDEV_j002_3673719.trc:
ORA-12012: 작업 "SYS"."ORA$AT_SQ_SQL_SW_3530"의 자동 실행중 오류 발생
ORA-38153: 소프트웨어 에디션이 SQL 계획 관리와 호환되지 않습니다.
ORA-06512: "SYS.DBMS_SPM_INTERNAL",  6420행
ORA-06512: "SYS.DBMS_SPM",  2840행
ORA-06512:  34행
2026-06-03T22:00:04.562055+09:00
TABLE SYS.WRI$_OPTSTAT_HISTHEAD_HISTORY: ADDED INTERVAL PARTITION SYS_P2405 (46175) VALUES LESS THAN (TO_DATE(' 2026-06-04 00:00:00', 'SYYYY-MM-DD HH24:MI:SS', 'NLS_CALENDAR=GREGORIAN'))
TABLE SYS.WRI$_OPTSTAT_HISTGRM_HISTORY: ADDED INTERVAL PARTITION SYS_P2408 (46175) VALUES LESS THAN (TO_DATE(' 2026-06-04 00:00:00', 'SYYYY-MM-DD HH24:MI:SS', 'NLS_CALENDAR=GREGORIAN'))
2026-06-04T22:00:02.234411+09:00
Errors in file /koem/oracle/diag/rdbms/unidev/UNIDEV/trace/UNIDEV_j002_3875968.trc:
ORA-12012: 작업 "SYS"."ORA$AT_SQ_SQL_SW_3533"의 자동 실행중 오류 발생
ORA-38153: 소프트웨어 에디션이 SQL 계획 관리와 호환되지 않습니다.
ORA-06512: "SYS.DBMS_SPM_INTERNAL",  6420행
ORA-06512: "SYS.DBMS_SPM",  2840행
ORA-06512:  34행
2026-06-04T22:00:02.742014+09:00
TABLE SYS.WRI$_OPTSTAT_HISTHEAD_HISTORY: ADDED INTERVAL PARTITION SYS_P2409 (46176) VALUES LESS THAN (TO_DATE(' 2026-06-05 00:00:00', 'SYYYY-MM-DD HH24:MI:SS', 'NLS_CALENDAR=GREGORIAN'))
TABLE SYS.WRI$_OPTSTAT_HISTGRM_HISTORY: ADDED INTERVAL PARTITION SYS_P2412 (46176) VALUES LESS THAN (TO_DATE(' 2026-06-05 00:00:00', 'SYYYY-MM-DD HH24:MI:SS', 'NLS_CALENDAR=GREGORIAN'))
2026-06-04T22:00:11.755499+09:00
Thread 1 cannot allocate new log, sequence 144
Private strand flush not complete
  Current log# 2 seq# 143 mem# 0: /koem/oradata/redo/redo02.log
2026-06-04T22:00:14.758557+09:00
Thread 1 advanced to log sequence 144 (LGWR switch),  current SCN: 41990311647287
  Current log# 3 seq# 144 mem# 0: /koem/oradata/redo/redo03.log



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
{id: null, key: "log_path", value: "/koem/oracle/diag/rdbms/unidev/UNIDEV/trace/alert_UNIDEV.log", sortOrder: 1}
,
{id: null, key: "fatal_error_patterns", value: "ORA-12012|ORA-00600|ORA-07445|ORA-04031|ORA-01578|ORA-00060|cannot allocate new log", sortOrder: 2}
]

# inspection_script

# -*- coding: utf-8 -*-

import re
import shlex
from .common._base import BaseCheck

INSPECTION_NAME = "DB 로그 파일 점검"
DEFAULT_LOG_PATH = "/koem/oracle/diag/rdbms/unidev/UNIDEV/trace/alert_UNIDEV.log"
DEFAULT_FATAL_PATTERNS = "ORA-12012|ORA-00600|ORA-07445|ORA-04031|ORA-01578|ORA-00060|cannot allocate new log"


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

    def run(self):
        raw_account = self.get_threshold_var(
            "oracle_account", default=self.DEFAULT_ORACLE_ACCOUNT, value_type="str"
        )
        raw_path = self.get_threshold_var(
            "log_path", default=DEFAULT_LOG_PATH, value_type="str"
        )
        raw_patterns = self.get_threshold_var(
            "fatal_error_patterns", default=DEFAULT_FATAL_PATTERNS, value_type="str"
        )
        patterns = self._parse_list(raw_patterns)
        thresholds = {
            "oracle_account": str(raw_account or "").strip(),
            "log_path": str(raw_path or "").strip(),
            "fatal_error_patterns": patterns,
        }
        oracle_account = str(raw_account or "").strip() or self.DEFAULT_ORACLE_ACCOUNT
        try:
            log_path = self._validate_absolute_path(raw_path, "log_path")
        except ValueError as exc:
            return self._failure("점검 설정 오류", str(exc), thresholds)
        if not patterns:
            return self._failure(
                "점검 설정 오류", "fatal_error_patterns 값이 비어 있습니다.", thresholds
            )
        command = "tail -100 " + shlex.quote(log_path)
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
                message = str(INSPECTION_NAME) + " 명령 실행에 실패했습니다."
            return self._failure(
                error,
                message,
                thresholds,
                metrics=metrics,
                stdout=stdout,
                stderr=stderr,
            )
        if not stdout:
            return self._failure(
                "출력 파싱 실패",
                "최근 로그 출력이 비어 있습니다.",
                thresholds,
                metrics=metrics,
                stdout=stdout,
            )
        matches = []
        for line in stdout.splitlines():
            lowered = line.lower()
            found = [pattern for pattern in patterns if pattern.lower() in lowered]
            if found:
                matches.append({"line": line.strip(), "patterns": found})
        metrics.update(
            {
                "log_line_count": len(stdout.splitlines()),
                "fatal_match_count": len(matches),
                "fatal_matches": matches,
            }
        )
        if matches:
            reason = (
                "최근 100줄에서 설정된 치명적 오류 패턴이 %s건 확인되었습니다."
                % len(matches)
            )
            return self._failure(
                "치명적 오류 로그 발견",
                reason,
                thresholds,
                metrics=metrics,
                stdout=stdout,
            )
        reason = "최근 100줄에서 설정된 치명적 오류 패턴이 발견되지 않았습니다."
        return self.ok(metrics=metrics, message=reason)


CHECK_CLASS = Check
