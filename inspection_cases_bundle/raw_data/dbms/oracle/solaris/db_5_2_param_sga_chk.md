# 영역
파라미터 점검

# 세부 점검항목
공유메모리(SGA) 파라미터 점검

# 점검 내용
DB에 접속하는 모든 사용자가 공유해서 사용하는 메모리로 물리 메모리 대비 적절한 값으로 설정되어 있는지 점검

# 구분
권고

# 명령어1 - OS 물리 메모리 변수 필요
```bash
sqlplus -S /nolog <<EOF
CONNECT / AS SYSDBA
SHOW PARAMETERS sga
EXIT;
EOF
```
# 명령어2 - OS 물리 메모리까지 출력하는 명령어, solaris 환경에서는 명령마다 프롬프트가 출력되어 확인 필요..
```
echo "=====Physical Memory====="
PHYS_MEM=$(prtconf | awk '/Memory size:/ {printf "%.0f\n", $3/1024}')

echo "${PHYS_MEM} GB"
echo ""
echo "=====Oracle SGA Parameter====="
echo "
show parameter sga
exit;
" | sqlplus -S / as sysdba
```

# 출력 결과1 (테스트 서버: 172.18.8.91)
```text
oratips@exTMStotalDB1:~$ sqlplus -S /nolog <<EOF
> CONNECT / AS SYSDBA
> SHOW PARAMETERS sga
> EXIT;
> EOF

NAME                                 TYPE        VALUE
------------------------------------ ----------- ------------------------------
allow_group_access_to_sga            boolean     TRUE
lock_sga                             boolean     FALSE
pre_page_sga                         boolean     TRUE
sga_max_size                         big integer 100G
sga_min_size                         big integer 0
sga_target                           big integer 100G
unified_audit_sga_queue_size         integer     1048576
```

# 출력 결과2 (테스트 서버: 172.18.8.91)
```text
oratips@exTMStotalDB1:~$ echo "=====Physical Memory====="
=====Physical Memory=====
oratips@exTMStotalDB1:~$ PHYS_MEM=$(prtconf | awk '/Memory size:/ {printf "%.0f\n", $3/1024}')
oratips@exTMStotalDB1:~$
oratips@exTMStotalDB1:~$ echo "${PHYS_MEM} GB"
254 GB
oratips@exTMStotalDB1:~$ echo ""

oratips@exTMStotalDB1:~$ echo "=====Oracle SGA Parameter====="
=====Oracle SGA Parameter=====
oratips@exTMStotalDB1:~$ echo "
> show parameter sga
> exit;
> " | sqlplus -S / as sysdba

NAME                                 TYPE        VALUE
------------------------------------ ----------- ------------------------------
allow_group_access_to_sga            boolean     TRUE
lock_sga                             boolean     FALSE
pre_page_sga                         boolean     TRUE
sga_max_size                         big integer 100G
sga_min_size                         big integer 0
sga_target                           big integer 100G
unified_audit_sga_queue_size         integer     1048576

```
# 설명
- sga_target: 오라클 DB가 동적으로 사용할 메모리의 목표값을 나타냄. 시스템이 실제로 얼마나 많은 메모리를 SGA에 할당할 것인지를 결정하는 값임. 시스템의 물리 메모리와 비교하여, 이 값이 너무 낮으면 DB 성능에 영향을 미칠 수 있고, 너무 높으면 시스템의 다른 프로세스에 영향을 줄 수 있음. 따라서 물리 메모리와의 균형을 잘 맞추는 것이 중요함. 
- sga_max_size: SGA가 사용할 수 있는 최대 메모리 크기를 설정한 값임. sga_target 값은 이 sga_max_size 범위 내에서만 조정될 수 있음. SGA가 커질 수 있는 최대 크기를 제한하는 값이기 때문에, 시스템의 물리 메모리보다 너무 큰 값으로 설정되면 메모리 부족 문제(예: 스와핑)가 발생할 수 있음.

SGA Target Usage Ratio(%) = sga_target / OS 물리 메모리 = 물리 메모리 대비 Oracle SGA(sga_target) 비율
SGA Max Usage Ratio(%) = sga_max_size / OS 물리 메모리 = 물리 메모리 대비 Oracle SGA 최대 사용 가능 크기(sga_max_size) 비율
※ 비율이 임계치 이상일 경우 sga_max_size 및 sga_target 설정값 점검 필요

# 임계치
sga_target_usage_ratio(ex.70%)
sga_max_usage_ratio(ex.70%)


# 판단기준
- **양호**: SGA Target Usage Ratio(%), SGA Max Usage Ratio(%)가 `sga_target_usage_ratio`, `sga_max_usage_ratio` 값을 넘지 않는 상태
- **경고**: SGA Target Usage Ratio(%), SGA Max Usage Ratio(%)가 `sga_target_usage_ratio`, `sga_max_usage_ratio` 값을 넘는 상태
- **확인 필요**: 명령어 수행 실패 또는 출력 결과를 확인할 수 없는 경우
