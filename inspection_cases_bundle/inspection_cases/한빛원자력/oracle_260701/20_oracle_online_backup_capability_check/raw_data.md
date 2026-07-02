# 영역
BACKUP

# 세부 점검 항목
온라인 백업 가능 여부

# 점검 내용
Oracle 온라인 백업 또는 시점 복구 가능 설정을 Windows 기준으로 점검합니다.

# 구분
권고

# 명령어
```powershell
$OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); @'
SET HEADING OFF FEEDBACK OFF VERIFY OFF PAGESIZE 0
SELECT 'log_mode|' || log_mode FROM v$database;
SELECT 'force_logging|' || force_logging FROM v$database;
SELECT 'flashback_on|' || flashback_on FROM v$database;
EXIT;
'@ | sqlplus -S / as sysdba
```

# 출력 결과
```text
log_mode|ARCHIVELOG
force_logging|YES
flashback_on|NO
```

# 설명
- ARCHIVELOG 여부와 force logging 설정은 온라인 백업 및 시점 복구 가능 여부에 직접 연결됩니다.
- 운영 정책에 따라 flashback 사용 여부도 함께 확인할 수 있습니다.

# 환경별 치환 값
- `ORACLE_SQLPLUS_PATH`: 현재값 `sqlplus`
- 명령어 치환 위치: `sqlplus`

# 임계치
- `required_log_mode`: `ARCHIVELOG`
- `required_force_logging`: `YES`

# 판단기준
- **정상**: 온라인 백업과 시점 복구에 필요한 핵심 설정이 확보되어 있습니다.
- **불량**: 온라인 백업 관련 설정이 운영 기준에 미달합니다.
