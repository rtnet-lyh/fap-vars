# 영역
프로세스 기동상태

# 세부 점검항목
DB 접속 상태 점검

# 점검 내용
DB가 기동되어 있으나 실제 이상없이 DB가 접속 가능하는지 점검(SQL 커맨드 모드로 접근하여 명령어 수행 상태 정상 점검)

# 구분
필수

# 명령어
```bash
sqlplus -S /nolog <<EOF
CONNECT / AS SYSDBA
SELECT 'DB is accessible' AS STATUS FROM dual;
EXIT;
EOF
```

# 출력 결과
```text
[OS: Rocky 9.4] 추출된 결과입니다.
slunidb-dev241:/home/oracle> sqlplus -S /nolog <<EOF
> CONNECT / AS SYSDBA
> SELECT 'DB is accessible' AS STATUS FROM dual;
> EXIT;
> EOF

STATUS
----------------
DB is accessible

slunidb-dev241:/home/oracle>




---
```

# 설명
- 접속(`sqlplus`)을 통해 데이터베이스의 오픈 상태와 접근 가능 여부를 확인합니다.

# 임계치
접속 및 쿼리 성공 여부

# 판단기준
- **양호**: DB 접속 및 쿼리가 정상 수행됨
- **경고**: DB 연결 실패 혹은 에러 반환
- **확인 필요**: 수집된 쿼리 결과 포맷 오류 또는 확인 불가
