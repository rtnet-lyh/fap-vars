# 영역
프로세스 기동상태

# 세부 점검항목
DB 접속 상태 점검

# 점검 내용
DB가 기동되어 있으나 실제 이상없이 DB가 접속 가능하는지 점검(SQL 커맨드 모드로 접근하여 명령어 수행 상태 정상 점검)

# 구분
필수

# 명령어
```bash
sqlplus -S /nolog << EOF
connect / as sysdba
select 'DB is accessible' from dual;
exit;
EOF
```

# 출력 결과 (테스트 서버: 172.18.8.91)
```text
oratips@exTMStotalDB1:~$ sqlplus -S /nolog << EOF
> connect / as sysdba
> select 'DB is accessible' from dual;
> exit;
> EOF

'DBISACCESSIBLE'
----------------
DB is accessible
```

# 설명
- 출력에 'DB is accessible'가 표시되면, DB가 정상적으로 작동 중이며, 접속이 가능하다는 것을 의미함
- 출력에 'DB is accessible' 메시지가 나타나지 않거나, SQL*Plus에서 오류 메시지가 나타난다면, DB 접속에 문제가 있음을 뜻함. DB가 기동되지 않았거나, 네트워크 문제, 권한 문제, 등의 점검이 필요 

# 임계치

# 판단기준
- **양호**: 출력에 'DB is accessible'가 표시된 상태
- **경고**: 출력에 'DB is accessible' 메시지가 나타나지 않거나, SQL*Plus에서 오류 메시지가 나타난 상태
- **확인 필요**: 대상 프로세스가 없거나 sqlplus 명령을 사용할 수 없는 상태
