# 영역
로그 점검

# 세부 점검항목
Dump파일 생성 여부 확인(DB 오류 발생시 생성)

# 점검 내용
DB가 문제 발생시 생성되는 trace(dump)파일로 원인 분석에 주로 사용되며 원인 파일을 위한 파일 점검

# 구분
필수

# 명령어
```bash
ls -ltr /koem/oracle/diag/rdbms/unidev/UNIDEV/trace/*.trc 2>/dev/null | tail -5
```

# 출력 결과
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

# 설명
- `alert.log` 및 `listener.log`, `*.trc` 등의 파일 내용을 점검하여 DB와 리스너에서 발생한 오류나 경고를 파악합니다.

# 임계치
에러 로깅 빈도 및 치명적 에러 존재 여부

# 판단기준
- **양호**: 시스템 장애를 유발할 수 있는 치명적인 에러 로그가 없음
- **경고**: 서비스 지연이나 장애를 일으키는 에러 다수 발생
- **확인 필요**: 파일 경로 오류 등으로 로그 확인 불가
