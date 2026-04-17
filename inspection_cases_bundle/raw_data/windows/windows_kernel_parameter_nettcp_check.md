# 영역
KERNEL PARAMETER

# 세부 점검항목
Kernel Parameter Check

# 점검 내용
Windows TCP 커널 파라미터 조회 가능 여부와 설정 확인

# 구분
권고

# 명령어
```powershell
$ErrorActionPreference = 'Stop'; $tcp = @(); $available = [bool](Get-Command Get-NetTCPSetting -ErrorAction SilentlyContinue); if ($available) { $tcp = @(Get-NetTCPSetting | Select-Object SettingName, AutoTuningLevelLocal, CongestionProvider, EcnCapability) }; [pscustomobject]@{ get_net_tcp_setting_available = $available; tcp_settings = $tcp } | ConvertTo-Json -Compress -Depth 6
```

# 출력 결과
```json
{"get_net_tcp_setting_available":true,"tcp_settings":[{"SettingName":"InternetCustom","AutoTuningLevelLocal":"Normal","CongestionProvider":"CTCP","EcnCapability":"Disabled"}]}
```

# 설명
- Get-NetTCPSetting으로 Windows TCP 설정을 조회한다.
- cmdlet을 사용할 수 없으면 OS 버전 또는 권한을 확인하고 수동 점검으로 대체한다.

# 임계치
없음

# 판단기준
- **양호**: Get-NetTCPSetting 조회가 정상 수행되는 경우
- **주의**: cmdlet을 사용할 수 없어 수동 확인이 필요한 경우
