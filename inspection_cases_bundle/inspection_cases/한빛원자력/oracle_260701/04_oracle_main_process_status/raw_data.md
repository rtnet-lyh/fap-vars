# 영역
PROCESS

# 세부 점검 항목
메인 프로세스 기동 상태

# 점검 내용
Oracle Windows 서비스와 메인 프로세스 기동 상태를 점검합니다.

# 구분
필수

# 명령어
```powershell
$OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); Get-Service -Name 'OracleServiceHBDEV' | Select-Object Name, Status, StartType | Format-Table -AutoSize; Get-Process -Name 'oracle' -ErrorAction SilentlyContinue | Select-Object ProcessName, Id, @{Name='CPU';Expression={"{0:N1}" -f ($_.CPU -as [double])}}, WS | Format-Table -AutoSize
```

# 출력 결과
```text
Name                Status StartType
----                ------ ---------
OracleServiceHBDEV Running Automatic



ProcessName   Id CPU          WS
-----------   -- ---          --
oracle      4388 0.0 16248414208
```

# 설명
- Windows에서는 `Get-Service`로 서비스 상태를, `Get-Process`로 실제 프로세스 존재 여부를 함께 확인합니다.
- 서비스는 Running인데 프로세스가 없거나 반대로 프로세스만 남은 상태는 비정상으로 봅니다.

# 환경별 치환 값
- `ORACLE_DB_SERVICE_NAME`: 현재값 `OracleServiceHBDEV`
- 명령어 치환 위치: `Get-Service -Name 'OracleServiceHBDEV'`
- 프로세스명: 현재값 `oracle`
- 명령어 치환 위치: `Get-Process -Name 'oracle'`

# 임계치
- `required_service_status`: `Running`
- `required_starttype`: `Automatic`

# 판단기준
- **정상**: 서비스와 프로세스가 모두 정상 실행 중입니다.
- **불량**: 서비스 중지, 시작 유형 이상, 프로세스 누락 중 하나라도 확인됩니다.
