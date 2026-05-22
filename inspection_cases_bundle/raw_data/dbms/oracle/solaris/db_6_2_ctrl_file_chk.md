# 영역
이중화 점검

# 세부 점검항목
컨트롤파일 (DB 정보파일) 이중화

# 점검 내용
오라클 DB 서버를 운영하기 위한 필수 정보를 가지고 있는 파일로 파일 손상에 대비하여 2개 이상의 이중화 파일(물리적, 논리적)로 구성되어 있는지 점검

# 구분
권고

# 명령어
```bash
sqlplus -S /nolog <<EOF
CONNECT / AS SYSDBA
set linesize 200
col name format a40
SELECT * FROM V\$controlfile;
EXIT;
EOF
```

# 출력 결과 (테스트 서버: 172.18.8.91)
```text
oratips@exTMStotalDB1:~$ sqlplus -S /nolog <<EOF
> CONNECT / AS SYSDBA
> set linesize 200
> col name format a40
> SELECT * FROM V\$controlfile;
> EXIT;
> EOF

STATUS  NAME                                     IS_ BLOCK_SIZE FILE_SIZE_BLKS     CON_ID
------- ---------------------------------------- --- ---------- -------------- ----------
        /TTIPS_DATA01/TTIPS/control01.ctl        NO       16384           1494          0
        /TTIPS_DATA02/TTIPS/control02.ctl        NO       16384           1494          0

```

# 설명
- STATUS: CURRENT는 현재 사용중으로 정상, INVALID인 경우, 해당 제어 파일을 재생성하거나 복구하는 것이 필요. 
- NAME: 제어 파일의 경로가 정상적으로 표시되면 문제가 없으며, 이상이 발견되면 수정해야 함. 
※ NAME 항목에 2개의 서로 다른 컨트롤 파일 경로가 나열되어 있고, 이는 물리적으로 2개의 컨트롤 파일이 존재하고 있고 이중화가 되어 있음을 나타냄.

# 임계치


# 판단기준
- **양호**: 출력값의 STATUS값이 CURRENT이거나 NAME에 Control File이 2개 이상으로 서로 다른 마운트 포인트에 분산 구성된 경우
- **경고**: 출력값의 STATUS값이 INVALID이거나 NAME에 Control File이 1개만 구성된 경우
- **확인 필요**: 명령어 수행 실패 또는 출력 결과를 확인할 수 없는 경우
