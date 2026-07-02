# 영역
LOG

# 세부 점검 항목
리스너/접속 로그 점검

# 점검 내용
PostgreSQL 접속 관련 로그에서 연결 실패와 지연 징후를 점검합니다.

# 구분
권고

# 명령어
```powershell
$OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); Select-String -Path 'C:\Program Files\PostgreSQL\16\data\log\*.log' -Pattern 'login failed|access denied|timeout|connection refused|disconnect|TNS-' -CaseSensitive:$false | Select-Object -First 20
```

# 출력 결과
```text
C:\Program Files\PostgreSQL\16\data\log\listener.log:44: connection refused from APP01
```

# 설명
- WAS-DB 구간 접속 문제는 서비스 이상보다 먼저 로그에 드러나는 경우가 많습니다.
- 연결 거부, 인증 실패, 타임아웃, 세션 끊김 흔적을 우선적으로 확인합니다.

# 환경별 치환 값
- `POSTGRES_LOG_PATH`: 현재값 `C:\Program Files\PostgreSQL\16\data\log\*.log`
- 명령어 치환 위치: `C:\Program Files\PostgreSQL\16\data\log\*.log`

# 임계치
- `max_connection_error_count`: `0`
- `failure_keywords`: `login failed,timeout,connection refused`

# 판단기준
- **정상**: 접속 오류 흔적이 없습니다.
- **불량**: 인증/연결 실패 로그가 반복됩니다.
