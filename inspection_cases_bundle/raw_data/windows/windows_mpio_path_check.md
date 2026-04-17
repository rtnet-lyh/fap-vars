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
if (Get-Command Get-MPIOSetting -ErrorAction SilentlyContinue) { Get-MPIOSetting | Select-Object PathVerificationState,PathVerificationPeriod,RetryCount,RetryInterval,DiskTimeoutValue,@{N='LoadBalancePolicy';E={Get-MSDSMGlobalDefaultLoadBalancePolicy 2>$null}} | Format-List; mpclaim.exe -s -d } else { 'MPIO 誘몄꽕移??먮뒗 誘몄??? }
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
- 일반 Windows 11 환경에서는 MPIO가 설치되지 않아 대상 아님 성격으로 해석될 수 있습니다.

# 임계치
- `expected_policy_keyword`: `round`
- `failure_keywords`: 없음

# 판단기준
- **정상**: 실패 경로가 없고 부하분산 정책이 기대 키워드를 만족합니다.
- **대상 아님**: MPIO가 설치되지 않은 일반 환경입니다.
- **경고**: failed/offline 경로가 감지되거나 정책이 기대와 다릅니다.


