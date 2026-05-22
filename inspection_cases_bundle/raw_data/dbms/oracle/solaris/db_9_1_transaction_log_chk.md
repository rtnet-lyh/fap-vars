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
connect / as sysdba
set feedback off
select GROUP#, MEMBERS, BYTES/1024/1024 AS SIZE_MB, STATUS
from V\$log;
exit;
EOF
```

# 출력 결과 (테스트 서버: 172.18.8.91)
```text
oratips@exTMStotalDB1:~$ sqlplus -S /nolog <<EOF
> connect / as sysdba
> set feedback off
> select GROUP#, MEMBERS, BYTES/1024/1024 AS SIZE_MB, STATUS
> from V\$log;
> exit;
> EOF

    GROUP#    MEMBERS    SIZE_MB STATUS
---------- ---------- ---------- ----------------
         1          2       2048 INACTIVE
         2          2       2048 ACTIVE
         3          2       2048 INACTIVE
         4          2       2048 CURRENT
         5          2       2048 INACTIVE
         6          2       2048 CURRENT
         7          2       2048 INACTIVE
         8          2       2048 INACTIVE
         9          2       2048 ACTIVE
        10          2       2048 INACTIVE

```

# 설명
- SIZE_MB: Redo 로그 파일의 크기를 MB 단위로 나타냄. 로그 파일 크기가 적절하지 않을 경우, 성능 문제를 방지하기 위해 크기를 재조정하거나 추가 로그 파일 생성 권고. 
※ 오라클 환경에서 ‘트랜잭션 로그’와 ‘리두 로그’는 같은 개념을 의미함. 
※ 트랜잭션 로그가 무한정 커지지 않도록, 각 로그 파일의 크기와 사용 상태를 주기적으로 점검하여 적절하게 관리해야 함. 
※ 보통 오라클 데이터베이스에서는 각 트랜잭션 로그 그룹에 속한 로그 파일의 크기를 동일하게 설정하는 것이 권장되지만, 반드시 동일할 필요는 없음. 트랜잭션 파일의 크기는 시스템의 설정에 따라 다를 수 있음.

# 임계치
min_logfile_size: 로그 파일의 최소 크기(MB)

# 판단기준
- **양호**: 출력값의 MEMBERS값이 2 이상이며, STATUS값이 'INACTIVE', 'ACTIVE', 'CURRENT'이고, SIZE_MB 값이 최소크기(`min_logfile_size`) 이상인 상태
- **경고**: 출력값의 MEMBERS값이 2 미만이거나,  STATUS값이 'INVALID', 'STALE' 등이며, SIZE_MB 값이 최소크기(`min_logfile_size`) 미만인 상태
- **확인 필요**: 명령어 수행 실패 또는 출력 결과를 확인할 수 없는 경우
