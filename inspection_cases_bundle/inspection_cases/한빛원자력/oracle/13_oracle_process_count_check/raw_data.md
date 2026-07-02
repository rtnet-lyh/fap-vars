# 영역
PARAMETER

# 세부 점검 항목
최대 프로세스/세션 수 사용률

# 점검 내용
Oracle 최대 연결/세션 수 대비 현재 사용량을 Windows DB 클라이언트 기준으로 점검합니다.

# 구분
필수

# 명령어
```powershell
$OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); sqlplus -S / as sysdba @session_usage.sql
```

# 출력 결과
```text
max_connections|300
current_sessions|42
max_used_sessions|66
```

# 설명
- 최대 세션 수에 근접하면 신규 접속 실패와 서비스 지연이 발생할 수 있습니다.
- 현재 접속 수와 최대 사용 이력을 함께 보면 여유율 판단이 쉽습니다.

# 환경별 치환 값
- `ORACLE_SQLPLUS_PATH`: 현재값 `sqlplus`
- 명령어 치환 위치: `sqlplus`

# 임계치
- `max_session_usage_percent`: `80.0`
- `max_used_session_warning_percent`: `90.0`

# 판단기준
- **정상**: 현재 세션 수가 허용 범위 내입니다.
- **불량**: 세션 사용률이 높아 접속 실패 위험이 있습니다.
