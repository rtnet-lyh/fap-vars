# 영역
BACKUP

# 세부 점검 항목
DB 백업 상태

# 점검 내용
MySQL 최근 백업 이력과 Windows 백업 파일 존재 여부를 함께 점검합니다.

# 구분
필수

# 명령어
```powershell
$OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); Get-ChildItem -Path 'C:\Backup\MySQL\*' -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 10 Name, Length, LastWriteTime; mysql -NBe "SHOW BINARY LOGS;"
```

# 출력 결과
```text
FULL|2026-06-29 02:00:00|SUCCESS|C:\Backup\MySQL\full_20260629.bak
```

# 설명
- 백업 산출물과 DB 내부 백업 이력을 같이 봐야 실제 복구 가능성을 판단할 수 있습니다.
- 최신 백업 시각, 유형, 상태, 파일 존재 여부를 확인합니다.

# 환경별 치환 값
- `MYSQL_CLIENT_PATH`: 현재값 `mysql`
- 명령어 치환 위치: `mysql`
- `MYSQL_BACKUP_PATH`: 현재값 `C:\Backup\MySQL\*`
- 명령어 치환 위치: `C:\Backup\MySQL\*`

# 임계치
- `max_backup_age_hours`: `24`
- `required_backup_status`: `SUCCESS`

# 판단기준
- **정상**: 최근 백업이 정상 완료되었고 산출물도 확인됩니다.
- **불량**: 백업 실패, 누락, 과도한 경과시간이 확인됩니다.
