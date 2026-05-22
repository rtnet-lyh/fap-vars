# 영역
로그 점검

# 세부 점검항목
DB 엔진 로그 파일 점검

# 점검 내용
DB 엔진에서 발생되는 Internal(DB 엔진 내부 기능) 에러 로그에 대한 점검

# 구분
필수

# 명령어 - db_log_dir 변수: /TTIPS_LOG01/diag/rdbms/ttips/TTIPS1/trace
```bash
egrep -i "ORA-|error|failure|warning|corrupt|internal|deadlock|timeout" {{ db_log_dir }}/alert_*.log
```

# 출력 결과 (테스트 서버: 172.18.8.91)
```text
oratips@exTMStotalDB1:~$ egrep -i "ORA-|error|failure|warning|corrupt|internal|deadlock|timeout" /TTIPS_LOG01/diag/rdbms/ttips/TTIPS1/trace/alert_*.log
ORA-24962: 접속 문자열의 구문을 분석할 수 없습니다. 오류 = 303
Errors in file /TTIPS_LOG01/diag/rdbms/ttips/TTIPS1/trace/TTIPS1_ora_26492.trc:
ORA-24962: 접속 문자열의 구문을 분석할 수 없습니다. 오류 = 303
Errors in file /TTIPS_LOG01/diag/rdbms/ttips/TTIPS1/trace/TTIPS1_ora_26495.trc:
ORA-24962: 접속 문자열의 구문을 분석할 수 없습니다. 오류 = 303
Fatal NI connect error 12170.
  Tns error struct:
Fatal NI connect error 12170.
  Tns error struct:
```

# 설명
- ORA-01536: space quota exceeded for tablespace 'USERS' - 테이블스페이스의 공간이 초과되면 사용량을 확인하고, 필요 시 공간을 늘리거나 데이터를 삭제해야 함. 
- error: data file is missing - 데이터 파일이 누락되면 해당 파일의 존재를 확인하고, 복구하거나 재생성해야 함. 
- failure: unable to open database - 데이터베이스가 열리지 않으면 상태를 점검하고, 필요시 다시 시작해야 함. 
- warning: potential configuration issue detected - 구성 문제의 경고가 발생하면 파일을 점검하고 필요한 수정을 해야 함. 
- corrupt: data block corrupted (file # 1, block # 12345) - 데이터 블록이 손상되면 관련 블록을 확인하고 복구 작업을 해야 함. 
- deadlock detected while waiting for resource - 데드락이 발생하면 관련 세션을 종료하여 문제를 해결해야 함. 
- timeout: connection attempt timed out - 연결 시도가 시간 초과되면 네트워크를 점검하고 리스너 및 클라이언트 설정을 조정해야 함. 
※ 기본 경로로 나타냈으며, 사용자가 임의로 경로를 변경했을 경우 수정되어야 함.

# 임계치

# 판단기준
- **양호**: 출력값에 결과가 나오지 않은 상태
- **경고**: 출력값에 결과가 나온 상태
- **확인 필요**: 로그 파일 및 경로가 존재하지 않는 경우
