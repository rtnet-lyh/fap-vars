# 영역
BACKUP

# 세부 점검 항목
환경 설정 파일 백업 점검

# 점검 내용
MSSQL 설정 파일 백업본의 존재 여부와 최신성을 Windows 경로 기준으로 점검합니다.

# 구분
권고

# 명령어
```powershell
$OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); Get-ChildItem -Path 'C:\Backup\MSSQL\*' -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object Name, Length, LastWriteTime
```

# 출력 결과
```text
Name            Length LastWriteTime
config_backup.conf  12288  2026-06-29 03:00:00
```

# 설명
- 장애 복구 시 설정 파일 백업이 없으면 서비스 복구 시간이 크게 늘어날 수 있습니다.
- 파일 개수, 수정 시각, 크기를 함께 보고 너무 오래된 백업은 재생성을 검토합니다.

# 환경별 치환 값
- `MSSQL_BACKUP_PATH`: 현재값 `C:\Backup\MSSQL\*`
- 명령어 치환 위치: `C:\Backup\MSSQL\*`

# 임계치
- `required_config_backup`: `true`
- `max_config_backup_age_days`: `7`

# 판단기준
- **정상**: 주요 설정 파일 백업이 존재하고 최신성이 유지됩니다.
- **불량**: 설정 파일 백업이 없거나 오래되었습니다.
