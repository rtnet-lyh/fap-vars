# 영역
백업점검

# 세부 점검항목
온라인 백업 가능 여부 점검

# 점검 내용
DB 운영 중 온라인 백업이 가능하도록 아카이브 모드 상태가 활성화 되었는지 점검

# 구분
권고

# 명령어
```bash
sqlplus -S /nolog <<EOF
connect / as sysdba
set feedback off
select log_mode from v\$database;
exit;
EOF
```

# 출력 결과 (테스트 서버: 172.18.8.91)
```text
oratips@exTMStotalDB1:~$ sqlplus -S /nolog <<EOF
> connect / as sysdba
> set feedback off
> select log_mode from v\$database;
> exit;
> EOF

LOG_MODE
------------
ARCHIVELOG

```

# 설명
- 로그 모드가 NOARCHIVELOG로 표시된다면, 데이터베이스의 안정적인 온라인 백업을 위해 ARCHIVELOG 모드로 전환 필요. 전환을 위해 데이터베이스를 재시작하고 ARCHIVELOG 모드를 활성화해야 하며, 이는 즉각적인 조치 권고

# 임계치

# 판단기준
- **양호**: 출력값의 LOG_MODE가 'ARCHIVELOG'인 상태
- **경고**: 출력값의 LOG_MODE가 'ARCHIVELOG'가 아닌 상태
- **확인 필요**: 명령어 수행 실패 또는 출력 결과를 확인할 수 없는 경우
