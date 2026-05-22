# 영역
백업점검

# 세부 점검항목
DB 백업 상태 점검

# 점검 내용
백업 형태(Begin/End, Rman, Exp 등), 날짜, 로그, 파일수 등을 점검하여 장애 시 완전 복구 가능 여부 점검

# 구분
필수

# 명령어
```bash
sqlplus -S /nolog <<EOF
rman target / <<EOF
LIST BACKUP SUMMARY;
EXIT;
EOF
```

# 출력 결과 (테스트 서버: 172.18.8.91)
```text
oratips@exTMStotalDB1:~$ rman target / <<EOF
> LIST BACKUP SUMMARY;
> EXIT;
> EOF

Recovery Manager: Release 19.0.0.0.0 - Production on Thu May 21 15:03:00 2026
Version 19.27.0.0.0

Copyright (c) 1982, 2019, Oracle and/or its affiliates.  All rights reserved.

connected to target database: TTIPS (DBID=179220281)

RMAN> LIST BACKUP SUMMARY;
using target database control file instead of recovery catalog

List of Backups
===============
Key     TY LV S Device Type Completion Time #Pieces #Copies Compressed Tag
------- -- -- - ----------- --------------- ------- ------- ---------- ---
29528   B  F  A SBT_TAPE    06-MAY-26       1       1       NO         TAG20260506T033323
29534   B  F  A SBT_TAPE    06-MAY-26       1       1       NO         TAG20260506T034054
29536   B  F  A SBT_TAPE    06-MAY-26       1       1       NO         TAG20260506T034351
.
.
32737   B  F  A SBT_TAPE    21-MAY-26       1       1       NO         TAG20260521T034240
32738   B  F  A SBT_TAPE    21-MAY-26       1       1       NO         TAG20260521T034407
32739   B  F  A SBT_TAPE    21-MAY-26       1       1       NO         TAG20260521T130012
32740   B  F  A SBT_TAPE    21-MAY-26       1       1       NO         TAG20260521T130029

RMAN> EXIT;

Recovery Manager complete.

```

# 설명
- Completion Time: 백업이 완료된 시간을 나타내며, 백업이 정기적으로 수행되지 않았다면 백업 스케줄을 재검토하고 수정이 필요. 데이터 손실을 방지하고 최신 데이터를 복구하기 위해서는 주기적으로 백업이 완료되어야 하므로, 백업이 완료된 시간을 확인함으로써 점검할 수 있음.
※ 사용자 정의값인 `backup_threshold_days`일 이내 정상 백업 수행 권고
- (현재 시간 - Completion Time) > `backup_threshold_days` 인 경우 비정상

# 임계치
backup_threshold_days: 마지막 백업 완료 시점으로부터 허용 가능한 경과 일수(일 단위)

# 판단기준
- **양호**: 현재 시간과 마지막 백업 완료시간(Completion Time) 값이 `backup_threshold_days` 이내인 상태 
- **경고**: 현재 시간과 마지막 백업 완료시간(Completion Time) 값이 `backup_threshold_days` 를 초과한 상태
- **확인 필요**: 명령어 수행 실패 또는 출력 결과를 확인할 수 없는 경우
