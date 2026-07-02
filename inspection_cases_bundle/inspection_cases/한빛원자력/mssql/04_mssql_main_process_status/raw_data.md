# 영역
PROCESS

# 세부 점검 항목
메인 프로세스 기동 상태

# 점검 내용
MSSQL Windows 서비스와 메인 프로세스 기동 상태를 점검합니다.

# 구분
필수

# 명령어
```powershell
$OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); Get-Service -Name 'MSSQLSERVER' | Select-Object Name, Status, StartType; Get-Process -Name 'sqlservr' -ErrorAction SilentlyContinue | Select-Object ProcessName, Id, CPU, WS
```

# 출력 결과
```text
Name              Status  StartType
MSSQLSERVER Running Automatic

ProcessName Id   CPU  WS
sqlservr      4120 3.5  524288000
```

# 설명
- Windows에서는 `Get-Service`로 서비스 상태를, `Get-Process`로 실제 프로세스 존재 여부를 함께 확인합니다.
- 서비스는 Running인데 프로세스가 없거나 반대로 프로세스만 남은 상태는 비정상으로 봅니다.

# 환경별 치환 값
- `MSSQL_SERVICE_NAME`: 현재값 `MSSQLSERVER`
- 명령어 치환 위치: `Get-Service -Name 'MSSQLSERVER'`
- 프로세스명: 현재값 `sqlservr`
- 명령어 치환 위치: `Get-Process -Name 'sqlservr'`

# 임계치
- `required_service_status`: `Running`
- `required_starttype`: `Automatic`

# 판단기준
- **정상**: 서비스와 프로세스가 모두 정상 실행 중입니다.
- **불량**: 서비스 중지, 시작 유형 이상, 프로세스 누락 중 하나라도 확인됩니다.
