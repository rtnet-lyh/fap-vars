# 영역
PROCESS

# 세부 점검 항목
리스너/서비스 포트 기동 상태

# 점검 내용
Oracle 접속 포트 1521 의 Listen 상태와 관련 서비스를 점검합니다.

# 구분
필수

# 명령어
```powershell
$OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); Get-NetTCPConnection -State Listen -LocalPort 1521 | Select-Object LocalAddress, LocalPort, State, OwningProcess; Get-Service -Name 'OracleOraDB19Home1TNSListener' -ErrorAction SilentlyContinue | Select-Object Name, Status
```

# 출력 결과
```text
LocalAddress LocalPort State  OwningProcess
0.0.0.0      1521      Listen 4188

Name                          Status
OracleOraDB19Home1TNSListener Running
```

# 설명
- Windows에서는 `Get-NetTCPConnection` 으로 실제 Listen 포트를 확인합니다.
- 서비스가 떠 있어도 포트가 열리지 않으면 실제 접속은 실패할 수 있습니다.

# 환경별 치환 값
- `ORACLE_PORT`: 현재값 `1521`
- 명령어 치환 위치: `Get-NetTCPConnection -LocalPort 1521`
- `ORACLE_LISTENER_SERVICE_NAME`: 현재값 `OracleOraDB19Home1TNSListener`
- 명령어 치환 위치: `Get-Service -Name 'OracleOraDB19Home1TNSListener'`

# 임계치
- `required_port`: `1521`
- `required_state`: `Listen`

# 판단기준
- **정상**: 포트가 Listen 상태이고 관련 서비스도 Running 입니다.
- **불량**: 포트 미개방 또는 서비스 비정상입니다.
