# 영역
LOG

# 세부 점검 항목
DB 로그 파일 점검

# 점검 내용
MySQL 오류 로그에서 주요 장애 키워드를 검색합니다.

# 구분
필수

# 명령어
```powershell
$OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); Select-String -Path 'C:\ProgramData\MySQL\MySQL Server 8.0\Logs\*.err' -Pattern 'error|failure|insufficient|full|corrupt|deadlock|ORA-|FATAL|PANIC' -CaseSensitive:$false | Select-Object -First 20
```

# 출력 결과
```text
C:\ProgramData\MySQL\MySQL Server 8.0\Logs\error.log:125: ERROR tablespace full detected
```

# 설명
- Windows에서는 `Select-String` 으로 로그 파일의 장애 키워드를 빠르게 검색합니다.
- 공간 부족, 데이터 손상, deadlock, 기동 실패 흔적이 있는지 우선 확인합니다.

# 환경별 치환 값
- `MYSQL_LOG_PATH`: 현재값 `C:\ProgramData\MySQL\MySQL Server 8.0\Logs`
- 명령어 치환 위치: `C:\ProgramData\MySQL\MySQL Server 8.0\Logs\*.err`

# 임계치
- `max_error_count`: `0`
- `failure_keywords`: `error,failure,full,corrupt,deadlock`

# 판단기준
- **정상**: 심각한 오류 키워드가 확인되지 않습니다.
- **불량**: 장애 징후 로그가 탐지됩니다.
