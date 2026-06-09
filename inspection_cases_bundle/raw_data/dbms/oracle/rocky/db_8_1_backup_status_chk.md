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
rman TARGET / << EOF
LIST BACKUP SUMMARY;
EXIT;
EOF
```

# 출력 결과
```text
[OS: Rocky 9.4] 추출된 결과입니다.
slunidb-dev241:/koem/oracle/diag/rdbms/unidev/UNIDEV/trace> rman TARGET / << EOF
> LIST BACKUP SUMMARY;
> EXIT;
> EOF

Recovery Manager: Release 19.0.0.0.0 - Production on Fri Jun 5 14:08:48 2026
Version 19.25.0.0.0

Copyright (c) 1982, 2019, Oracle and/or its affiliates.  All rights reserved.

connected to target database: UNIDEV (DBID=1665036402)

RMAN> LIST BACKUP SUMMARY;
using target database control file instead of recovery catalog
specification does not match any backup in the repository


RMAN> EXIT;

Recovery Manager complete.




---
```

# 설명
- `rman` 도구 등을 사용하여 백업 수행 결과 및 온라인 백업 가능 설정 등을 확인합니다.

# 임계치
최근 정상 백업 존재 여부

# 판단기준
- **양호**: 백업이 에러 없이 정상적으로 수행 및 완료됨
- **경고**: 백업 실패 이력 또는 오래된 백업만 존재
- **확인 필요**: 실행 에러 또는 백업 내역 확인 불가
