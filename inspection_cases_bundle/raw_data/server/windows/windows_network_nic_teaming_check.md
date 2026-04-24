# 영역
NETWORK

# 세부 점검 항목
NIC Teaming(LBFO) 상태

# 점검 내용
LBFO Team 구성 여부와 팀 상태, 팀 멤버의 Active/Standby 상태를 점검합니다.

# 구분
필수

# 명령어
```powershell
$OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); if (Get-Command Get-NetLbfoTeam -ErrorAction SilentlyContinue) { $teams = Get-NetLbfoTeam -ErrorAction SilentlyContinue; if ($teams) { @($teams | ForEach-Object { $team = $_; Get-NetLbfoTeamMember -Team $team.Name | Select-Object @{N='GROUPNAME';E={$team.Name}}, @{N='TEAMSTATE';E={$team.Status}}, @{N='MODE';E={$team.TeamingMode}}, @{N='NIC';E={$_.Name}}, @{N='STATE';E={$_.OperationalMode}}, @{N='ACTIVE';E={if ($_.OperationalMode -eq 'Active') {'Yes'} else {'No'}}}, @{N='ROLE';E={$_.AdministrativeMode}} }) | ConvertTo-Json -Depth 3 } else { 'NIC Teaming(LBFO): 미구성 또는 미지원' } } else { 'NetLbfo cmdlet 없음' }
```

# 출력 결과
```text
NIC Teaming(LBFO): 미구성 또는 미지원
```

# 설명
- LBFO Team 구성 여부와 팀 멤버 상태를 확인합니다.
- LBFO cmdlet이 없거나 팀이 구성되지 않은 경우에도 점검 실패로 처리합니다.

# 임계치
- `max_down_or_degraded_team_count`: `0`
- `max_failed_member_count`: `0`
- `failure_keywords`: 없음

# 판단기준
- **정상**: 팀 상태가 정상이고 실패 멤버 수가 허용 범위 이내입니다.
- **불량**: LBFO 기능 또는 팀 구성이 없거나, Down/Degraded 팀 또는 비정상 멤버 수가 임계치를 초과합니다.


