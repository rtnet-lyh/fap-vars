# 영역
트랜젝션 로그 점검

# 세부 점검항목
트랜잭션(데이터베이스 논리적 상태 변경) 로그 사이즈 점검

# 점검 내용
DB 운영 시 발생 되는 트랜잭션 로그에 대해 무한정 늘어나는 경우를 대비하여 로그 사이즈 점검, 저장 공간 Full 로 인한 서비스 불가 발생에 따름

# 구분
필수

# 명령어
```bash
sqlplus -S /nolog <<EOF
CONNECT / AS SYSDBA
SELECT GROUP#, MEMBERS, BYTES/1024/1024 AS SIZE_MB, STATUS FROM V$LOG;
EXIT;
EOF
```

# 출력 결과
```text
[OS: Rocky 9.4] 추출된 결과입니다.
slunidb-dev241:/koem/oracle/diag/rdbms/unidev/UNIDEV/trace> sqlplus -S /nolog <<EOF
CONNECT / AS SYSDBA
SELECT GROUP#, MEMBERS, BYTES/1024/1024 AS SIZE_MB, STATUS
FROM V\\$LOG;
EXIT;
EOF

    GROUP#    MEMBERS    SIZE_MB STATUS
---------- ---------- ---------- ----------------
         1          1        200 INACTIVE
         2          1        200 INACTIVE
         3          1        200 CURRENT



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
