# 영역
DISK

# 세부 점검항목
Path 이중화 점검

# 점검 내용
Windows MPIO 기능 및 mpclaim 경로 상태 확인

# 구분
필수

# 명령어
```powershell
$ErrorActionPreference = 'Stop'; $feature = Get-WindowsFeature Multipath-IO -ErrorAction SilentlyContinue; $claims = ''; if (Get-Command mpclaim.exe -ErrorAction SilentlyContinue) { $claims = (mpclaim.exe -s -d | Out-String) }; $installed = if ($feature) { [bool]$feature.Installed } else { $false }; [pscustomobject]@{ mpio_installed = $installed; mpclaim_available = [bool](Get-Command mpclaim.exe -ErrorAction SilentlyContinue); mpclaim_output = $claims.Trim() } | ConvertTo-Json -Compress -Depth 6
```

# 출력 결과
```json
{"mpio_installed":true,"mpclaim_available":true,"mpclaim_output":"MPIO Disk0 DSM OK"}
```

# 설명
- Multipath-IO 기능 설치 여부와 mpclaim 조회 결과를 확인한다.
- MPIO 기능이 없으면 대상미해당이며, SAN 다중 경로 구성 서버에서는 벤더 DSM 상태를 함께 확인한다.

# 임계치
없음

# 판단기준
- **양호**: MPIO 기능과 mpclaim 조회가 수행되는 경우
- **대상미해당**: Multipath-IO 기능이 설치되어 있지 않은 경우
