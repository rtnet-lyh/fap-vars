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

DBMS-ORACLE-ROCKY-DB-3-1-OS-MEMORY

# is_required

필수

# inspection_name

물리적 메모리 사용률

# inspection_content

DB 프로세스가 사용중인 물리적 메모리 사용률을 점검하여 Swapping(메모리 부족) 현상이 발생되지 않도록 적절한 메모리 수치값 점검

# inspection_command

```bash
ps -eo pid,comm,%mem,rss,vsz | grep ora_ | grep -v grep
```

# inspection_output

```text
[OS: Rocky 9.4] 추출된 결과입니다.
slunidb-dev241:/home/oracle> ps -eo pid,comm,%mem,rss,vsz | grep ora_ | grep -v grep
 139563 ora_w002_unidev  0.3 234132 24968156
 359607 ora_m004_unidev  1.4 971776 24976828
 475615 ora_w005_unidev  0.5 388292 24967132
 524302 ora_w009_unidev  0.3 221316 24968148
 652248 ora_w004_unidev  0.4 299096 24967128
 708294 ora_w001_unidev  0.3 224584 24970200
 728381 ora_w00e_unidev  0.2 171772 24967124
 811760 ora_m006_unidev  1.3 876288 24976832
 888371 ora_w003_unidev  0.2 162896 24967132
1165533 ora_w00n_unidev  0.2 170216 24967128
1367946 ora_w00m_unidev  0.4 290612 24967128
1370749 ora_w000_unidev  0.3 220548 24968156
1401053 ora_w00f_unidev  0.2 167968 24967124
1409942 ora_w00d_unidev  0.3 254804 24968152
1611468 ora_w00g_unidev  0.2 163964 24968148
1814507 ora_w00r_unidev  0.5 377792 24967124
1934845 ora_w00k_unidev  0.6 405480 24967128
2216715 ora_m001_unidev  1.4 919808 24976832
2228026 ora_w008_unidev  0.2 142524 24968148
2236433 ora_w00u_unidev  0.2 140712 24968148
2241975 ora_w00c_unidev  0.3 210304 24967128
2261611 ora_w00a_unidev  0.3 248604 24967128
2456046 ora_w006_unidev  0.4 284404 24967128
2702423 ora_w00s_unidev  0.2 134168 24968152
2900095 ora_w00i_unidev  0.5 340832 24968148
2905076 ora_m002_unidev  1.3 881536 24976824
2926526 ora_w00q_unidev  0.4 316544 24967128
3005503 ora_w00p_unidev  0.1 129388 24968152
3148433 ora_w00o_unidev  0.3 197400 24967124
3205195 ora_w00l_unidev  0.3 239516 24968148
3228641 ora_w00b_unidev  0.4 282324 24968152
3229780 ora_pmon_unidev  0.1 79744 24966028
3229784 ora_clmn_unidev  0.0 63872 24966032
3229788 ora_psp0_unidev  0.0 64896 24968140
3229792 ora_vktm_unidev  0.0 63360 24966032
3229798 ora_gen0_unidev  0.0 64512 24966028
3229802 ora_mman_unidev  1.5 996608 24966032
3229808 ora_scmn_unidev  0.2 178828 25066544
3229811 ora_diag_unidev  0.0 63232 24966032
3229813 ora_scmn_unidev  0.1 108808 25050828
3229816 ora_dbrm_unidev  0.9 648192 24967584
3229820 ora_vkrm_unidev  0.1 67328 24966032
3229822 ora_svcb_unidev  0.0 64384 24967056
3229824 ora_pman_unidev  0.0 64256 24966032
3229828 ora_dia0_unidev  0.1 109568 24976528
3229830 ora_dbw0_unidev  1.7 1167372 24984532
3229834 ora_dbw1_unidev  1.7 1157512 24980308
3229838 ora_lgwr_unidev  0.1 113152 24967064
3229842 ora_ckpt_unidev  0.3 227968 24966044
3229846 ora_lg00_unidev  0.1 106240 24966040
3229848 ora_smon_unidev  0.8 560640 24968172
3229852 ora_lg01_unidev  0.1 105216 24966036
3229856 ora_reco_unidev  0.1 82688 24967096
3229860 ora_lreg_unidev  0.1 94092 24974660
3229866 ora_pxmn_unidev  0.0 63488 24966036
3229872 ora_mmon_unidev  0.9 649168 25090928
3229874 ora_mmnl_unidev  0.1 98816 24966044
3229876 ora_d000_unidev  0.0 60416 24968552
3229878 ora_s000_unidev  0.0 58880 24967580
3229880 ora_tmon_unidev  0.0 64000 24966032
3234399 ora_tt00_unidev  0.1 74496 24988632
3234401 ora_tt01_unidev  0.0 62976 24966028
3234403 ora_tt02_unidev  0.0 62720 24966024
3234407 ora_smco_unidev  0.1 65664 24966028
3234415 ora_aqpc_unidev  0.1 76672 24966040
3234419 ora_cjq0_unidev  0.5 374272 24988112
3234765 ora_qm02_unidev  0.1 75648 24966032
3234769 ora_q002_unidev  0.1 91264 24968184
3234771 ora_q003_unidev  0.4 267648 24976396
3235857 ora_cl00_unidev  0.0 62336 24966028
3235859 ora_cl01_unidev  0.0 62336 24966028
3235861 ora_cl02_unidev  0.0 62208 24966024
3235863 ora_cl03_unidev  0.0 62080 24966028
3235865 ora_cl04_unidev  0.0 62080 24966024
3236940 ora_w00j_unidev  0.6 454432 24967132
3654123 ora_w007_unidev  0.4 303156 24967128
3729045 ora_w00v_unidev  0.4 306956 24967128
3840410 ora_w00h_unidev  0.3 225608 24968152
4174110 ora_w00t_unidev  0.3 230572 24967128


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

RESOURCE_KIND = "memory"
INSPECTION_NAME = "Oracle 프로세스 메모리 사용률"
COMMAND = "ps -eo pid,comm,%mem,rss,vsz | grep ora_ | grep -v grep"
PROCESS_PATTERN = re.compile(
    "^\\s*(\\d+)\\s+(ora_\\S+)\\s+([0-9]+(?:\\.[0-9]+)?)\\s+(\\d+)\\s+(\\d+)\\s*$"
)


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
