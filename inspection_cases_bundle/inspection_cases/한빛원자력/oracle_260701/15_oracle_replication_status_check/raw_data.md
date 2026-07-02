# 영역
HA

# 세부 점검 항목
Active-Standby/복제 상태

# 점검 내용
Oracle Data Guard 또는 유사 복제 구성을 Windows 환경의 DB 클라이언트 명령으로 점검합니다.

# 구분
필수

# 명령어
```powershell
$OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); @'
SET HEADING OFF FEEDBACK OFF VERIFY OFF PAGESIZE 0
SELECT 'database_role|' || database_role || '|open_mode|' || open_mode || '|log_mode|' || log_mode FROM v$database;
SELECT 'switchover_status|' || switchover_status FROM v$database;
EXIT;
'@ | sqlplus -S / as sysdba
```

# 출력 결과
```text
database_role|PRIMARY|open_mode|READ WRITE|log_mode|ARCHIVELOG
switchover_status|NOT ALLOWED
```

# 설명
- 복제 여부를 확인할 때는 데이터베이스 역할, 오픈 모드, 아카이브 로그 모드를 먼저 확인합니다.
- Data Guard를 쓰는 환경이면 switchover 가능 상태와 standby 적용 상태를 추가 점검해야 합니다.

# 환경별 치환 값
- `ORACLE_SQLPLUS_PATH`: 현재값 `sqlplus`
- 명령어 치환 위치: `sqlplus`

# 임계치
- `required_database_role`: `PRIMARY or PHYSICAL STANDBY`
- `required_log_mode`: `ARCHIVELOG`

# 판단기준
- **정상**: 역할과 로그 모드가 운영 정책에 부합합니다.
- **불량**: 복제 또는 절체 운영 기준에 맞지 않는 상태가 확인됩니다.
