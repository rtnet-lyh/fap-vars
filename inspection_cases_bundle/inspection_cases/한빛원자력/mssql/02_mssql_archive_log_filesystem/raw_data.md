# 영역
STORAGE

# 세부 점검 항목
아카이브/변경 로그 파일시스템 사용률

# 점검 내용
MSSQL 아카이브/변경 로그가 저장되는 Windows 볼륨 사용률을 점검합니다.

# 구분
필수

# 명령어
```powershell
$OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); Get-Volume | Where-Object { $_.Path -like 'C:\Program Files\Microsoft SQL Server\MSSQL16.MSSQLSERVER\MSSQL\Log*' -or $_.FileSystemLabel -like '*ARCH*' } | Select-Object DriveLetter, FileSystemLabel, SizeRemaining, Size
```

# 출력 결과
```text
DriveLetter FileSystemLabel SizeRemaining Size
D           ARCHIVE         75161927680 107374182400
```

# 설명
- 아카이브 로그, 바이너리 로그, WAL 보관 위치의 디스크 여유율을 확인합니다.
- 해당 볼륨이 가득 차면 백업/복구 및 트랜잭션 처리에 직접 영향이 갈 수 있습니다.

# 환경별 치환 값
- `MSSQL_LOG_ARCHIVE_PATH`: 현재값 `C:\Program Files\Microsoft SQL Server\MSSQL16.MSSQLSERVER\MSSQL\Log`
- 명령어 치환 위치: `C:\Program Files\Microsoft SQL Server\MSSQL16.MSSQLSERVER\MSSQL\Log`

# 임계치
- `max_archive_use_percent`: `80.0`
- `min_archive_avail_percent`: `20.0`

# 판단기준
- **정상**: 로그 보관 볼륨 사용률이 기준 이하입니다.
- **불량**: 로그 보관 볼륨 공간이 부족합니다.
