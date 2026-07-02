# 영역
STORAGE

# 세부 점검 항목
DB 시스템 로그 파일시스템 사용률

# 점검 내용
MySQL 시스템 로그가 저장되는 Windows 볼륨 사용률을 점검합니다.

# 구분
권고

# 명령어
```powershell
$OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); Get-Volume | Where-Object { $_.Path -like 'C:\ProgramData\MySQL\MySQL Server 8.0\Logs*' -or $_.FileSystemLabel -like '*LOG*' } | Select-Object DriveLetter, FileSystemLabel, SizeRemaining, Size
```

# 출력 결과
```text
DriveLetter FileSystemLabel SizeRemaining Size
E           DBLOG           42949672960 85899345920
```

# 설명
- DB 오류 로그와 운영 로그가 저장되는 드라이브의 여유 공간을 확인합니다.
- 로그 볼륨 부족은 장애 분석 정보 유실로 이어질 수 있습니다.

# 환경별 치환 값
- `MYSQL_LOG_PATH`: 현재값 `C:\ProgramData\MySQL\MySQL Server 8.0\Logs`
- 명령어 치환 위치: `C:\ProgramData\MySQL\MySQL Server 8.0\Logs\*.err`

# 임계치
- `max_log_fs_use_percent`: `80.0`
- `min_log_fs_avail_percent`: `20.0`

# 판단기준
- **정상**: 로그 볼륨 사용률이 안정적입니다.
- **불량**: 로그 저장 볼륨 공간이 부족합니다.
