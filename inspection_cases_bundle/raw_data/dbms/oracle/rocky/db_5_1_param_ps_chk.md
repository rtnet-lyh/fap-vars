# 영역
파라미터 점검

# 세부 점검항목
프로세스 개수 점검

# 점검 내용
DB에 설정된 최대 프로세스 개수 대비 DB 기동 후 현재시점까지 접속했던 세션 프로세스 개수에 대한 사용률 점검(초과 시 DB 접속 불가 및 서비스 지연)

# 구분
필수

# 명령어
```bash
sqlplus -S /nolog <<EOF
CONNECT / AS SYSDBA
SELECT value AS "Max Processes", (SELECT COUNT(*) FROM v$session) AS "Current Sessions", ROUND((SELECT COUNT(*) FROM v$session) / value * 100, 2) AS "Usage %" FROM v$parameter WHERE name = 'processes';
EXIT;
EOF
```

# 출력 결과
```text
[OS: Rocky 9.4] 추출된 결과입니다.
slunidb-dev241:/koem/oracle/diag/rdbms/unidev/UNIDEV/trace> sqlplus -S /nolog <<EOF
> CONNECT / AS SYSDBA
> SELECT
> value AS "Max Processes",
> (SELECT COUNT(*) FROM v\\$session) AS "Current Sessions",
> ROUND((SELECT COUNT(*) FROM v\\$session) / value * 100, 2) AS "Usage %"
> FROM v\\$parameter
> WHERE name = 'processes';
> EXIT;
> EOF

Max Processes
--------------------------------------------------------------------------------
Current Sessions    Usage %
---------------- ----------
1500
             168       11.2


---
```

# 설명
- `sqlplus`를 통해 시스템 리소스 한계치(Max Processes, SGA 설정 등)와 현재 사용량 통계를 조회합니다.

# 임계치
리소스 최대 한계점(예: Max Processes 초과 여부)

# 판단기준
- **양호**: 사용량이 임계치 이내에서 안정적으로 관리됨
- **경고**: 프로세스, SGA 등의 사용량이 한계치에 임박하거나 초과함
- **확인 필요**: 쿼리 실패 또는 수집 결과 포맷 불일치
