# 영역
로그 점검

# 세부 점검항목
Dump파일 생성 여부 확인(DB 오류 발생시 생성)

# 점검 내용
DB가 문제 발생시 생성되는 trace(dump)파일로 원인 분석에 주로 사용되며 원인 파일을 위한 파일 점검

# 구분
필수

# 명령어 - db_log_dir 변수: /TTIPS_LOG01/diag/rdbms/ttips/TTIPS1/trace
```bash
cd {{ db_log_dir }} && ls -ltr *.trc | tail -1
```

# 출력 결과 (테스트 서버: 172.18.8.91)
```text
oratips@exTMStotalDB1:~$ cd /TTIPS_LOG01/diag/rdbms/ttips/TTIPS1/trace && ls -ltr *.trc | tail -10
-rw-r-----   1 oratips  dba      5706845 May 21 16:06 TTIPS1_lms1_1024_3.trc
-rw-r-----   1 oratips  dba      6145929 May 21 16:06 TTIPS1_lms3_1028_3.trc
-rw-r-----   1 oratips  dba         1297 May 21 16:06 TTIPS1_j002_20909.trc
-rw-r-----   1 oratips  dba         1295 May 21 16:07 TTIPS1_j002_1418.trc
-rw-r-----   1 oratips  dba       855377 May 21 16:07 TTIPS1_ora_26472.trc
-rw-r-----   1 oratips  dba         5780 May 21 16:08 TTIPS1_j001_26905.trc
-rw-r-----   1 oratips  dba         1887 May 21 16:10 TTIPS1_j001_8185.trc
-rw-r-----   1 oratips  dba      5221152 May 21 16:10 TTIPS1_dbrm_1011.trc
-rw-r-----   1 oratips  dba      3931743 May 21 16:10 TTIPS1_vkrm_1013.trc
-rw-r-----   1 oratips  dba      78451948 May 21 16:11 TTIPS1_lmhb_1042.trc
```

# 설명
- 이 출력으로 덤프 파일이 생성되었는지 확인할 수 있으며, 파일이 여러 개일 경우 가장 최근 파일을 기준으로 분석을 시작할 수 있음
※ 가장 최근 생성된 trace(.trc) 파일을 확인하여 최근 오류 또는 dump 발새 ㅇ여부를 점검함
- trace 파일이 존재할 경우 최근 생성 시각 및 파일명을 기준으로 분석 수행 가능

# 임계치

# 판단기준  - .trc 파일 수동 점검 필요
- **양호**: 출력값에 trace 파일이 확인되지 않을 경우(=출력값이 없는 경우)
- **경고**: 출력값에 trace 파일이 확인된 경우(=출력값이 있는 경우)
- **확인 필요**: 로그 파일 및 경로가 존재하지 않는 경우
