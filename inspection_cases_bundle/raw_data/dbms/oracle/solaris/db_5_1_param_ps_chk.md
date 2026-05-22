# 영역
파라미터 점검

# 세부 점검항목
프로세스 개수 점검

# 점검 내용
DB에 설정된 최대 프로세스 개수 대비 DB 기동 후 현재시점까지 접속했던 세션 프로세스 개수에 대한 사용률 점검(초과 시 DB 접속 불가 및 서비스 지연)

# 구분
필수

# 명령어
```bash
sqlplus -S / as sysdba << EOF
set linesize 200 pagesize 100 feedback off

SELECT
	TO_NUMBER(value) AS "Max Processes",
	(SELECT COUNT(*) FROM v\$session) AS "Current Sessions",
	ROUND(((SELECT COUNT(*) FROM v\$session) / TO_NUMBER(value)) * 100, 2) AS "Usage Percentage"
FROM 	v\$parameter
WHERE
	name = 'processes';
EXIT;
EOF
```

# 출력 결과 (테스트 서버: 172.18.8.91)
```text
oratips@exTMStotalDB1:~$ sqlplus -S / as sysdba << EOF
> set linesize 200 pagesize 100 feedback off
>
> SELECT
> TO_NUMBER(value) AS "Max Processes",
> (SELECT COUNT(*) FROM v\$session) AS "Current Sessions",
> ROUND(((SELECT COUNT(*) FROM v\$session) / TO_NUMBER(value)) * 100, 2) AS "Usage Percentage"
> FROM v\$parameter
> WHERE
> name = 'processes';
> EXIT;
> EOF

Max Processes Current Sessions Usage Percentage
------------- ---------------- ----------------
        10000             2363            23.63
```

# 설명
- Max Processes: 최대 프로세스 개수는 데이터베이스의 요구 사항과 시스템 자원에 따라 적절히 설정해야 하며, 일반적으로 100 이상의 값을 유지하는 것이 좋음. 만약 이 값이 100 이하로 설정되어 있다면, 증가시키는 것이 필요. 
- Current Sessions: 현재 세션 수는 최대 프로세스를 넘지 않는 적당한 수로 유지되어야 함. 과할 경우 불필요한 세션을 종료하는 것이 필요. 
- Usage Percentage: 사용률은 90% 이하일 경우 정상으로 간주하며, 과도할 경우 최대 프로세스 수를 증가시키는 것이 필요. 
※ 해당 점검을 수행할 수 있는 일반적인 명령어는 없으며, SELECT 명령어는 오라클 데이터베이스에서 데이터를 조회하는 역할을 하며, 일반적으로 데이터베이스에 직접적인 영향을 주지 않음.

# 임계치
max_process_count: 최대 프로세스 개수
max_current_sessions: 최대 현재 세션 수
max_usage_percentage: 최대 사용률


# 판단기준
- **양호**: Max Processes 값이 `max_process_count`가 이상이며, Current Sessions가 `max_current_sessions`를 초과하지 않고, Current Sessions값이 `max_usage_percentage`값 이하일 경우
- **경고**: Max Processes 값이 `max_process_count`가 이하이며, Current Sessions가 `max_current_sessions`를 초과하지 않고, Current Sessions값이 `max_usage_percentage`값 초과일 경우
- **확인 필요**: 명령어 수행 실패 또는 출력 결과를 확인할 수 없는 경우
