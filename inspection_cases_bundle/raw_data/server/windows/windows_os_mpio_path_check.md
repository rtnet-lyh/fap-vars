# 영역
STORAGE

# 세부 점검 항목
MPIO 경로 HA 및 부하분산 정책

# 점검 내용
Get-MPIOSetting과 mpclaim 결과를 기준으로 MPIO 설정과 경로 상태를 점검합니다.

# 구분
필수

# 명령어
```powershell
$OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); if (Get-Command Get-MPIOSetting -ErrorAction SilentlyContinue) { Get-MPIOSetting | Select-Object PathVerificationState,PathVerificationPeriod,RetryCount,RetryInterval,DiskTimeoutValue,@{N='LoadBalancePolicy';E={Get-MSDSMGlobalDefaultLoadBalancePolicy 2>$null}} | Format-List; mpclaim.exe -s -d } else { 'MPIO 미설치 또는 미지원' }
```

# 출력 결과
```text
PathVerificationState : Enabled
PathVerificationPeriod : 30
RetryCount : 3
RetryInterval : 1
DiskTimeoutValue : 60
LoadBalancePolicy : Round Robin
```

# 설명
- MPIO 설치 여부, 부하분산 정책, failed/offline 경로 흔적을 함께 확인합니다.
- MPIO가 설치되어 있지 않거나 지원되지 않는 경우도 점검 실패로 처리합니다.

# 임계치
- `expected_policy_keyword`: `round`
- `failure_keywords`: 없음

# 판단기준
- **정상**: 실패 경로가 없고 부하분산 정책이 기대 키워드를 만족합니다.
- **불량**: MPIO가 설치되어 있지 않거나 지원되지 않거나, failed/offline 경로가 감지되거나 정책이 기대와 다릅니다.


