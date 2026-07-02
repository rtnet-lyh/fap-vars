# 영역
BACKUP

# 세부 점검 항목
DB 백업 상태

# 점검 내용
Oracle 최근 백업 이력과 Windows 백업 파일 존재 여부를 함께 점검합니다.

# 구분
필수

# 명령어
```powershell
$OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); Get-ChildItem -Path 'C:\Backup\Oracle\*.bak' -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 10 Name, Length, LastWriteTime; @'
SET HEADING OFF FEEDBACK OFF VERIFY OFF PAGESIZE 0
SELECT INPUT_TYPE || '|' || STATUS || '|' || TO_CHAR(END_TIME, 'YYYY-MM-DD HH24:MI:SS')
FROM (
    SELECT INPUT_TYPE, STATUS, END_TIME
    FROM V$RMAN_BACKUP_JOB_DETAILS
    ORDER BY END_TIME DESC
)
WHERE ROWNUM = 1;
EXIT;
'@ | sqlplus -S / as sysdba
```

# 출력 결과
```text
DB FULL|COMPLETED|2026-06-29 02:00:00|C:\Backup\Oracle\full_20260629.bak
```

# 설명
- 백업 산출물과 DB 내부 백업 이력을 같이 봐야 실제 복구 가능성을 판단할 수 있습니다.
- 최신 백업 시각, 유형, 상태, 파일 존재 여부를 확인합니다.

# 환경별 치환 값
- `ORACLE_SQLPLUS_PATH`: 현재값 `sqlplus`
- 명령어 치환 위치: `sqlplus`
- `ORACLE_DB_BACKUP_PATH`: 현재값 `C:\Backup\Oracle\*.bak`
- 명령어 치환 위치: `C:\Backup\Oracle\*.bak`

# 임계치
- `max_backup_age_hours`: `24`
- `required_backup_status`: `COMPLETED`

# 판단기준
- **정상**: 최근 백업이 정상 완료되었고 산출물도 확인됩니다.
- **불량**: 백업 실패, 누락, 과도한 경과시간이 확인됩니다.
