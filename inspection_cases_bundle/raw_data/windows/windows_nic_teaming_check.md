# 영역
NETWORK

# 세부 점검항목
NIC 이중화 점검

# 점검 내용
Windows NIC Teaming 구성 및 상태 확인

# 구분
권고

# 명령어
```powershell
$ErrorActionPreference = 'Stop'; $available = [bool](Get-Command Get-NetLbfoTeam -ErrorAction SilentlyContinue); $teams = @(); if ($available) { $teams = @(Get-NetLbfoTeam | Select-Object Name, Status, TeamingMode, LoadBalancingAlgorithm) }; [pscustomobject]@{ get_net_lbfo_team_available = $available; team_count = @($teams).Count; teams = $teams } | ConvertTo-Json -Compress -Depth 6
```

# 출력 결과
```json
{"get_net_lbfo_team_available":true,"team_count":1,"teams":[{"Name":"Team1","Status":"Up","TeamingMode":"SwitchIndependent","LoadBalancingAlgorithm":"Dynamic"}]}
```

# 설명
- Get-NetLbfoTeam으로 NIC Teaming 구성과 상태를 확인한다.
- Team 구성이 없을 때 require_nic_team 정책에 따라 실패 또는 확인 필요로 판단한다.

# 임계치
require_nic_team: false

# 판단기준
- **양호**: NIC Team 구성이 확인되는 경우
- **주의**: Team 구성이 없지만 필수 정책이 아닌 경우
- **경고**: require_nic_team이 true인데 Team 구성이 없는 경우
