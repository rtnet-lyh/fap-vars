# 영역
DBMS 리소스 사용률

# 세부 점검항목
테이블 스페이스 사용률 점검

# 점검 내용
DB 데이터가 저장되는 테이블 스페이스 영역의 사용률이 90% 이상을 사용할 경우 테이블 스페이스 공간 확보 대비

# 구분
필수

# 명령어
```bash
sqlplus -S /nolog <<EOF
CONNECT / AS SYSDBA
select * from DBA_TABLESPACE_USAGE_METRICS;
EXIT;
EOF
```

# 출력 결과
```text
[OS: Rocky 9.4] 추출된 결과입니다.
slunidb-dev241:/koem/oracle/diag/rdbms/unidev/UNIDEV/trace> sqlplus -S /nolog <<EOF
CONNECT / AS SYSDBA
select * from DBA_TABLESPACE_USAGE_METRICS;
EXIT;
EOF

TABLESPACE_NAME                USED_SPACE TABLESPACE_SIZE USED_PERCENT
------------------------------ ---------- --------------- ------------
ATFW                               196736         3932160   5.00325521
HDATA_1_GW8                       1318960         3932160   33.5428874
HDATA_2_GW8                       2121872         3932160   53.9619954
HDATA_3_GW8                         10768         3932160   .273844401
HDATA_4_GW8                        272000         3932160   6.91731771
HINDEX_1_GW8                        13184         3932160   .335286458
HINDEX_2_GW8                      3215936         7864320   40.8927409
HINDEX_3_GW8                        52992         3932160   1.34765625
HQDB_GW8                           819208         3932160   20.8335368
HQDB_X_GW8                         198288         3932160   5.04272461
SYSAUX                             128968         4194302    3.0748382

TABLESPACE_NAME                USED_SPACE TABLESPACE_SIZE USED_PERCENT
------------------------------ ---------- --------------- ------------
SYSTEM                             147264         4194302   3.51104904
TEMP                                    0         4194176            0
TSINTRA_1_GW8                     1024216         3932160   26.0471598
TSINTRA_2_GW8                      135112         3932160   3.43607585
TSINTRA_3_GW8                       76928         3932160   1.95638021
TSINTRA_4X_GW8                     272784         3932160   6.93725586
TSINTRA_4_GW8                      628864         3932160   15.9928385
TSINTRA_5X_GW8                        128         3932160   .003255208
TSINTRA_5_GW8                         128         3932160   .003255208
TSINTRA_X_GW8                      200608         3932160   5.10172526
UNDOTBS1                             1544         4194302   .036811846

TABLESPACE_NAME                USED_SPACE TABLESPACE_SIZE USED_PERCENT
------------------------------ ---------- --------------- ------------
USERS                                 344         4194302   .008201603

23 rows selected.


---
```

# 설명
- 딕셔너리(`DBA_TABLESPACE_USAGE_METRICS`, `V$LOG` 등)를 조회하여 테이블 스페이스 사용률, 리두 로그 파일 사이즈 등 용량을 점검합니다.

# 임계치
테이블 스페이스 및 로그 사이즈 최대 사용률

# 판단기준
- **양호**: 사용률이 한계치 이하로 여유가 있음
- **경고**: 한계치 초과 또는 자동 확장이 불가한 상태로 용량 임박
- **확인 필요**: 쿼리 실패 또는 수집 결과 포맷 불일치
