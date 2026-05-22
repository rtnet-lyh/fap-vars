# 영역
로그 점검

# 세부 점검항목
DB 로그 파일 점검

# 점검 내용
에러 코드(기동 및 정지, 테이블스 페이스 부족 에러, 백업 정상 유무, 데이터 파일 손상, Dead Lock 상태) 를 점검

# 구분
필수

# 명령어1 - db_log_dir 변수: /TTIPS_LOG01/diag/rdbms/ttips/TTIPS1/trace
```bash
egrep -i "error|failure|insufficient|full|corrupt|deadlock|detected" {{ db_log_dir }}/alert_*.log
```
# 명령어2 - db_log_dir 변수: /TTIPS_LOG01/diag/rdbms/ttips/TTIPS1/trace
```bash
egrep -i "ORA-01536|ORA-01110|ORA-00060|ORA-01578|RMAN-08136" /TTIPS_LOG01/diag/rdbms/ttips/TTIPS1/trace/alert_*.log
```

# 출력 결과1 (테스트 서버: 172.18.8.91)
```text
oratips@exTMStotalDB1:~$ egrep -i "error|failure|insufficient|full|corrupt|deadlock|detected" /TTIPS_LOG01/diag/rdbms/ttips/TTIPS1/trace/alert_*.log
Errors in file /TTIPS_LOG01/diag/rdbms/ttips/TTIPS1/trace/TTIPS1_ora_14566.trc:
Errors in file /TTIPS_LOG01/diag/rdbms/ttips/TTIPS1/trace/TTIPS1_ora_14568.trc:
Errors in file /TTIPS_LOG01/diag/rdbms/ttips/TTIPS1/trace/TTIPS1_ora_10978.trc:
Errors in file /TTIPS_LOG01/diag/rdbms/ttips/TTIPS1/trace/TTIPS1_ora_10983.trc:
```

# 설명
- ORA-01536: space quota exceeded for tablespace 'USERS' 
- 지정된 테이블스페이스의 공간 할당량이 초과되었음을 나타냄. 'USERS' 테이블스페이스의 사용량이 할당량을 초과했는지 확인함. 테이블스페이스를 확장하거나 불필요한 데이터를 삭제해야 함. 
- ORA-01110: data file 1 is missing
- 데이터 파일이 누락되었음을 나타냄. 해당 데이터 파일이 정상적으로 존재하는지 확인함. 누락된 데이터 파일을 복구하거나 재생성해야 함. 
- ORA-00060: deadlock detected while waiting for resource
- 두 개 이상의 세션이 서로를 기다리는 데드락 상태가 발생했음을 나타냄. 데드락 발생 시 관련 세션의 상태를 확인함. 대기 중인 세션을 종료하여 데드락 문제를 해결해야 함. 
- ORA-01578: ORACLE data block corrupted (file # 1, block # 12345) 
- 특정 데이터 블록이 손상되었음을 나타냄. 손상된 데이터 블록과 관련된 파일 번호를 확인함. 손상된 블록을 복구하기 위한 조치를 취해야 함. 
- RMAN-08136: WARNING: recovery is incomplete
- RMAN 백업 후 복구가 완료되지 않았음을 나타냄. RMAN 로그에서 복구 상태를 확인함. 복구 작업을 재시도하거나 추가적인 조치를 취해야 함. 

# 임계치

# 판단기준 - 명령어2 기준
- **양호**: 출력값에 결과가 나오지 않은 상태
- **경고**: 출력값에 결과가 나온 상태
- **확인 필요**: 로그 파일 및 경로가 존재하지 않는 경우
※ 로그 파일의 내용이 상이하기 때문에 오류 번호(ex. ORA-01536 등)으로 egrep 하여 판단기준 작성
