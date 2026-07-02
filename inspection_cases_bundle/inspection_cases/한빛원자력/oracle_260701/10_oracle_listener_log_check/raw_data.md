# 영역
LOG

# 세부 점검 항목
리스너/접속 로그 점검

# 점검 내용
Oracle 접속 관련 로그에서 연결 실패와 지연 징후를 점검합니다.

# 구분
권고

# 명령어
```powershell
$OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); Select-String -Path 'D:\oratrace\diag\tnslsnr\y143hbdev\listener\trace\listener.log' -Pattern 'login failed|access denied|timeout|connection refused|disconnect|TNS-' -CaseSensitive:$false | Select-Object -First 20
```

# 출력 결과
```text
D:\oratrace\diag	nslsnr\y143hbdev\listener	race\listener.log:25:TNS-12505: listener does not currently know of SID given in connect descriptor
D:\oratrace\diag	nslsnr\y143hbdev\listener	race\listener.log:36:TNS-12505: listener does not currently know of SID given in connect descriptor
```

# 설명
- WAS-DB 구간 접속 문제는 서비스 이상보다 먼저 로그에 드러나는 경우가 많습니다.
- 연결 거부, 인증 실패, 타임아웃, 세션 끊김 흔적을 우선적으로 확인합니다.

# 환경별 치환 값
- `ORACLE_LISTENER_LOG_PATH`: 현재값 `D:\oratrace\diag\tnslsnr\y143hbdev\listener\trace\listener.log`
- 명령어 치환 위치: `D:\oratrace\diag\tnslsnr\y143hbdev\listener\trace\listener.log`

# 임계치
- `max_listener_error_count`: `0`
- `failure_keywords`: `TNS-,login failed,timeout,connection refused`

# 판단기준
- **정상**: 반복적인 접속 실패 로그가 확인되지 않습니다.
- **불량**: 리스너 또는 애플리케이션 접속 이상 징후가 확인됩니다.
