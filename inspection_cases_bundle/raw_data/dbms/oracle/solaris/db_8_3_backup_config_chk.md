# 영역
백업점검

# 세부 점검항목
환경 설정 파일 백업 점검

# 점검 내용
장애 복구 시 기존 환경설정 확인을 위한 Config file backup 파일 백업 점검

# 구분
권고

# 명령어
```bash
rman target / <<EOF
LIST BACKUP OF SPFILE;
EXIT;
EOF
```

# 출력 결과 (테스트 서버: 172.18.8.91)
```text
oratips@exTMStotalDB1:~$ rman target / <<EOF
> LIST BACKUP OF SPFILE;
> EXIT;
> EOF

Recovery Manager: Release 19.0.0.0.0 - Production on Thu May 21 15:22:43 2026
Version 19.27.0.0.0

Copyright (c) 1982, 2019, Oracle and/or its affiliates.  All rights reserved.

connected to target database: TTIPS (DBID=179220281)

RMAN> LIST BACKUP OF SPFILE;
using target database control file instead of recovery catalog

List of Backup Sets
===================


BS Key  Type LV Size       Device Type Elapsed Time Completion Time
------- ---- -- ---------- ----------- ------------ ---------------
29528   Full    23.50M     SBT_TAPE    00:01:13     06-MAY-26
        BP Key: 29528   Status: AVAILABLE  Compressed: NO  Tag: TAG20260506T033323
        Handle: c-179220281-20260506-00   Media: @aaaac
  SPFILE Included: Modification time: 01-MAY-26
  SPFILE db_unique_name: TTIPS

BS Key  Type LV Size       Device Type Elapsed Time Completion Time
------- ---- -- ---------- ----------- ------------ ---------------
29534   Full    23.50M     SBT_TAPE    00:01:20     06-MAY-26
        BP Key: 29534   Status: AVAILABLE  Compressed: NO  Tag: TAG20260506T034054
        Handle: c-179220281-20260506-01   Media: @aaaac
  SPFILE Included: Modification time: 01-MAY-26
  SPFILE db_unique_name: TTIPS
.
.
BS Key  Type LV Size       Device Type Elapsed Time Completion Time
------- ---- -- ---------- ----------- ------------ ---------------
32738   Full    23.50M     SBT_TAPE    00:01:18     21-MAY-26
        BP Key: 32738   Status: AVAILABLE  Compressed: NO  Tag: TAG20260521T034407
        Handle: c-179220281-20260521-02   Media: @aaaac
  SPFILE Included: Modification time: 20-MAY-26
  SPFILE db_unique_name: TTIPS

BS Key  Type LV Size       Device Type Elapsed Time Completion Time
------- ---- -- ---------- ----------- ------------ ---------------
32740   Full    23.50M     SBT_TAPE    00:00:09     21-MAY-26
        BP Key: 32740   Status: AVAILABLE  Compressed: NO  Tag: TAG20260521T130029
        Handle: c-179220281-20260521-03   Media: @aaaac
  SPFILE Included: Modification time: 20-MAY-26
  SPFILE db_unique_name: TTIPS

RMAN> EXIT;

Recovery Manager complete.

```

# 설명
- Completion Time: SPFILE 백업이 완료된 시간을 나타내며, 정기적으로 최신 백업이 존재해야 함. 최신 백업이 없을 경우 즉각적인 백업 수행이 필요. 
※ SPFILE은 Server Parameter File로, 데이터베이스의 핵심 구성 설정을 저장하는 매개변수 파일임(데이터베이스가 구동될 때 필요한 모든 초기화 매개변수 설정을 포함함).
※ 출력이 길기 때문에 Completion Time에 원하는 날짜(사용자 정의값:`backup_reference_date`)의 문자열이 존재하는지 확인

# 임계치
backup_reference_date: 특정 날짜 문자열(예시. 21-MAY-26:일-월-연도)

# 판단기준
- **양호**: 출력값의 Comletion Time 값에 `backup_reference_date` 문자열이 있는 상태 
- **경고**: 출력값의 Comletion Time 값에 `backup_reference_date` 문자열이 없는 상태 
- **확인 필요**: 명령어 수행 실패 또는 출력 결과를 확인할 수 없는 경우
