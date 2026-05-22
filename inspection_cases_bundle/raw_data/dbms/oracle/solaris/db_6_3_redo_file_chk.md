# 영역
이중화 점검

# 세부 점검항목
리두로그 파일(데이터 변경사항 파일) 이중화

# 점검 내용
데이터 변경 사항을 기록하는 오라클 온라인 리두로그 파일로 파일 손상에 대비하여 2개 이상의 이중화(물리적, 논리적) 파일로 구성되어 있는지 점검

# 구분
권고

# 명령어
```bash
sqlplus -S /nolog <<EOF
CONNECT / AS SYSDBA
set linesize 200 pagesize 100 feedback off
col member format a40
col status format a10
col type format a10
SELECT * FROM V\$logfile;
EXIT;
EOF
```

# 출력 결과 (테스트 서버: 172.18.8.91)
```text
oratips@exTMStotalDB1:~$ sqlplus -S /nolog <<EOF
> CONNECT / AS SYSDBA
> set linesize 200 pagesize 100 feedback off
> col member format a40
> col status format a10
> col type format a10
> SELECT * FROM V\$logfile;
> EXIT;
> EOF

    GROUP# STATUS     TYPE       MEMBER                                   IS_     CON_ID
---------- ---------- ---------- ---------------------------------------- --- ----------
         1            ONLINE     /TTIPS_ORA01/TTIPS/redo01a.log           NO           0
         1            ONLINE     /TTIPS_ORA02/TTIPS/redo01b.log           NO           0
         3            ONLINE     /TTIPS_ORA01/TTIPS/redo03a.log           NO           0
         3            ONLINE     /TTIPS_ORA02/TTIPS/redo03b.log           NO           0
         4            ONLINE     /TTIPS_ORA01/TTIPS/redo04a.log           NO           0
         6            ONLINE     /TTIPS_ORA01/TTIPS/redo06a.log           NO           0
         7            ONLINE     /TTIPS_ORA01/TTIPS/redo07a.log           NO           0
         8            ONLINE     /TTIPS_ORA01/TTIPS/redo08a.log           NO           0
         8            ONLINE     /TTIPS_ORA02/TTIPS/redo08b.log           NO           0
         9            ONLINE     /TTIPS_ORA01/TTIPS/redo09a.log           NO           0
         9            ONLINE     /TTIPS_ORA02/TTIPS/redo09b.log           NO           0
        10            ONLINE     /TTIPS_ORA01/TTIPS/redo10a.log           NO           0
        10            ONLINE     /TTIPS_ORA02/TTIPS/redo10b.log           NO           0
         7            ONLINE     /TTIPS_ORA02/TTIPS/redo07b.log           NO           0
         4            ONLINE     /TTIPS_ORA02/TTIPS/redo04b.log           NO           0
         5            ONLINE     /TTIPS_ORA01/TTIPS/redo05a.log           NO           0
         5            ONLINE     /TTIPS_ORA02/TTIPS/redo05b.log           NO           0
         2            ONLINE     /TTIPS_ORA01/TTIPS/redo02a.log           NO           0
         2            ONLINE     /TTIPS_ORA02/TTIPS/redo02b.log           NO           0
         6            ONLINE     /TTIPS_ORA02/TTIPS/redo06b.log           NO           0

```

# 설명
- STATUS: 로그 파일의 현재 상태를 나타내며, 주로 "ONLINE" 상태로 표시됨. 이는 로그 파일이 정상적으로 운영 중임을 의미함. 모든 로그 파일이 "ONLINE" 상태여야 하며, 상태가 "INVALID" 또는 "STALE"로 표시될 경우, 해당 로그 파일을 복구하거나 교체하는 것이 권고. 
- TYPE: Redo Log 파일 상태 정보
- MEMBER: Redo Log 파일 경로 정보

※ 부연설명
- Oracle 버전에 따라 v$logfile의 STATUS 컬럼 값이 공백(NULL)으로 표시될 수 있음
- TYPE 값이 ONLINE인 경우 정상 운영 상태로 판단
- 동일 GROUP# 내 MEMBER가 2개 이상이며 서로 다른 디스크 또는 마운트 포인트에 구성되어 있는지 확인 필요
- Redo Log 파일은 장애 복구에 중요한 정보이므로 물리적으로 다른 경로에 두고 이중화 구성 권고

# 임계치
redo_group_member_count(= 동일한 GROUP# 숫자 확인)

# 판단기준
- **양호**: 동일 GROUP# 내 MEMBER가 2개 이상이며, 서로 다른 디스크 또는 마운트 포인트에 분산 구성된 경우
- **경고**: TYPE값이 ONLINE이 아니거나 동일 GROUP# 내 MEMBER가 1개만 존재하는 경우
- **확인 필요**: 명령어 수행 실패 또는 출력 결과를 확인할 수 없는 경우
