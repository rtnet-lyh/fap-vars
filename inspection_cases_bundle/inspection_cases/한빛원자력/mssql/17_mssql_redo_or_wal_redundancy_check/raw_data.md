# 영역
HA

# 세부 점검 항목
변경 로그 이중화 구성

# 점검 내용
MSSQL 변경 로그(WAL/redo/binlog) 구성과 분산 여부를 Windows 기준으로 점검합니다.

# 구분
필수

# 명령어
```powershell
$OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); sqlcmd -S localhost -E -Q "SET NOCOUNT ON; SELECT DB_NAME(database_id) AS db_name, name, physical_name FROM sys.master_files WHERE type_desc='LOG';"
```

# 출력 결과
```text
log01|C:\Program Files\Microsoft SQL Server\MSSQL16.MSSQLSERVER\MSSQL\DATA\log01.dat
log02|D:\DBLogs\log02.dat
```

# 설명
- 복구 핵심 로그가 한 경로에만 몰려 있으면 단일 장애점이 됩니다.
- 로그 보존 모드와 파일 분산 경로를 함께 확인합니다.

# 환경별 치환 값
- `MSSQL_DATA_PATH`: 현재값 `C:\Program Files\Microsoft SQL Server\MSSQL16.MSSQLSERVER\MSSQL\DATA`
- 명령어 치환 위치: `C:\Program Files\Microsoft SQL Server\MSSQL16.MSSQLSERVER\MSSQL\DATA`
- `MSSQL_SQLCMD_PATH`: 현재값 `sqlcmd`
- 명령어 치환 위치: `sqlcmd`

# 임계치
- `min_log_copy_count`: `2`
- `required_log_archive_enabled`: 제품별 보존 모드 활성화`

# 판단기준
- **정상**: 변경 로그 구성과 보존 정책이 적절합니다.
- **불량**: 로그 이중화 또는 보존 설정이 부족합니다.
