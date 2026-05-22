# 영역
이중화 점검

# 세부 점검항목
Active-Standby 구성 데이터 복제 정상 점검(벤더별 점검방법 상이)

# 점검 내용
이중화 DB에 대한 데이터 실시간 데이터 동기화가 문제없는지 점검

# 구분
권고

# 명령어
```bash
sqlplus -S / as sysdba <<EOF
ALTER SESSION SET NLS_LANGUAGE = 'AMERICAN';
set pagesize 100 linesize 300 feedback off heading on;
col destination format a40
col error format a30 

SELECT destination, status, error 
FROM v\$archive_dest 
WHERE destination IS NOT NULL;
exit
EOF
```

# 출력 결과 (테스트 서버: 172.18.8.91)
```text
oratips@exTMStotalDB1:~$ sqlplus -S / as sysdba <<EOF
> ALTER SESSION SET NLS_LANGUAGE = 'AMERICAN';
> set pagesize 100 linesize 300 feedback off heading on;
> col destination format a40
> col error format a30
>
> SELECT destination, status, error
> FROM v\$archive_dest
> WHERE destination IS NOT NULL;
> exit
> EOF

Session altered.


DESTINATION                              STATUS    ERROR
---------------------------------------- --------- ------------------------------
/TTIPS_ARCH                              VALID

```

# 설명
- STATUS: 상태가 VALID이면 정상이며, ERROR인 경우 문제 해결이 필요. 
- ERROR: 오류 메시지가 없으면 정상이며, 오류가 발생한 경우 원인 분석 및 조치 필요. 
※ target = 'STANDBY' 대상 archive dectination 상태 확인을 해야하나 archive_dest뷰에 TARGET 컬럼이 존재하지 않으므로, destination 및 status 값을 기준으로 Standby 대상여부와 정상 상태를 확인해야 함

# 임계치


# 판단기준
- **양호**: 출력값의 STATUS값이 VALID인 상태
- **경고**: 출력값의 STATUS값이 ERROR인 상태이며 ERROR값의 아카이브 오류 메시지 확인 필요
- **확인 필요**: 명령어 수행 실패 또는 출력 결과를 확인할 수 없는 경우
