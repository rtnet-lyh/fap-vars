# 영역
프로세스 기동상태

# 세부 점검항목
리스너(DB서비스 연결) 프로세스 기동 상태 점검

# 점검 내용
DB 서버와 클라이언트 간 접속 연결을 담당하는 리스너 프로세스 기동 여부 확인

# 구분
권고

# 명령어
```bash
ps aux | grep ora_smon
```

# 출력 결과 (테스트 서버: 172.18.8.91)
```text
oratips@exTMStotalDB2:/TTIPS_HOME/oracle/dbms/product/bin$
oratips@exTMStotalDB2:/TTIPS_HOME/oracle/dbms/product/bin$ ps aux | grep ora_smon
oratips   9379  0.0  0.010128 6640 pts/7    S 18:09:11  0:00 grep ora_smon
oratips  24703  0.0 39.8105663208105637024 ?        S 04:11:11  0:21 ora_smon_TTIPS2
```

# 설명
- 실행 중인 명령어가 ora_smon_mydb인지 확인하고, 잘못되었으면 올바른 인스턴스를 실행하도록 수정할 필요가 있음. 

# 임계치

# 판단기준
- **양호**: 결과에 Oracle DBMS 메인 프로세스(예시 출력:ora_smon_TTIPS2)가 출력될 경우
- **경고**: 결과에 Oracle DBMS 메인 프로세스(예시 출력:ora_smon_TTIPS2)가 출력되지 않을 경우
- **확인 필요**: 대상 프로세스가 없거나 출력에서 대상 프로세스를 찾지 못하는 상태
