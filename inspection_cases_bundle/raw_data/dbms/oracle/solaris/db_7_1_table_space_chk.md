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
connect / as sysdba
set feedback off
col usage_percent format 990.99
select tablespace_name, round(used_percent,2) as USAGE_PERCENT
from dba_tablespace_usage_metrics;
exit;
EOF
```

# 출력 결과 (테스트 서버: 172.18.8.91)
```text
oratips@exTMStotalDB1:~$ sqlplus -S /nolog <<EOF
> connect / as sysdba
> set feedback off
> col usage_percent format 990.99
> select tablespace_name, round(used_percent,2) as USAGE_PERCENT
> from dba_tablespace_usage_metrics;
> exit;
> EOF

TABLESPACE_NAME                USAGE_PERCENT
------------------------------ -------------
ECRS_DATA                              47.55
EXTLNK                                 70.13
OGG                                     2.99
SSOITS                                  0.55
SYSAUX                                 53.48
SYSTEM                                  7.55
TEMP                                    1.90
TIPSA_DATA                             73.41
TIPSA_IDX                              80.47
TIPSB_DATA                             76.01
TIPSB_IDX                              33.04

TABLESPACE_NAME                USAGE_PERCENT
------------------------------ -------------
TIPSC_DATA                             35.58
TIPSC_IDX                              61.76
TIPSD_DATA                             73.10
TIPSD_IDX                              77.38
TIPSE_DATA                             56.38
TIPSE_IDX                              60.45
TIPSF_DATA                             11.45
TIPSF_IDX                              37.36
TIPSG_DATA                             14.57
TIPSG_IDX                              47.99
TIPSH_DATA                              0.54

TABLESPACE_NAME                USAGE_PERCENT
------------------------------ -------------
TIPSH_IDX                               1.44
TIPSI_DATA                              8.59
TIPSI_IDX                              44.51
TIPSJ_DATA                             36.41
TIPSJ_IDX                              52.25
TIPSK_DATA                             43.29
TIPSK_IDX                              29.19
TIPS_DATA                              47.86
TIPS_IDX                               79.08
UNDOTBS1                               99.67
UNDOTBS2                               88.04

TABLESPACE_NAME                USAGE_PERCENT
------------------------------ -------------
USERS                                   0.23

```

# 설명
- USAGE_PERCENT: 테이블 스페이스의 사용률을 백분율로 나타내며, 사용률이 과도할 경우 경고 수준. 사용률이 과다하면 공간 부족 가능성이 높아지므로 즉각적인 공간 확보가 필요. 테이블 스페이스 확장이 권고되며, 심각할 경우 공간 확보가 필요.

# 임계치
max_ts_usage_pct: 테이블 스페이스 사용률(%)

# 판단기준
- **양호**: USAGE_PERCENT 값이 `max_ts_usage_pct` 미만인 경우
- **경고**: USAGE_PERCENT 값이 `max_ts_usage_pct` 이상인 경우
- **확인 필요**: 명령어 수행 실패 또는 출력 결과를 확인할 수 없는 경우
