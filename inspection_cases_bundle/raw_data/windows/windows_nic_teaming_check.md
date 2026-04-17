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
if (Get-Command Get-NetLbfoTeam -ErrorAction SilentlyContinue) { $teams = Get-NetLbfoTeam -ErrorAction SilentlyContinue; if ($teams) { $teams | ForEach-Object { $team = $_; Get-NetLbfoTeamMember -Team $team.Name | Select-Object @{N='GROUPNAME';E={$team.Name}}, @{N='TEAMSTATE';E={$team.Status}}, @{N='MODE';E={$team.TeamingMode}}, @{N='NIC';E={$_.Name}}, @{N='STATE';E={$_.OperationalMode}}, @{N='ACTIVE';E={if ($_.OperationalMode -eq 'Active') {'Yes'} else {'No'}}}, @{N='ROLE';E={$_.AdministrativeMode}} } | Format-Table -AutoSize } else { 'NIC Teaming(LBFO): 誘멸뎄???먮뒗 誘몄??? } } else { 'NetLbfo cmdlet ?놁쓬' }
```

# 출력 결과
```text
GROUPNAME  TEAMSTATE  MODE               NIC        STATE    ACTIVE  ROLE
TEAM01     Up         SwitchIndependent  Ethernet1  Active   Yes     Active
TEAM01     Up         SwitchIndependent  Ethernet2  Standby  No      Standby
```

# 설명
- LBFO cmdlet이 없거나 팀이 구성되지 않은 환경은 일반 Windows 11에서 흔한 케이스입니다.
- 팀 Down/Degraded 수와 실패 멤버 수를 기준으로 판단합니다.

# 임계치
- `max_down_or_degraded_team_count`: `0`
- `max_failed_member_count`: `0`
- `failure_keywords`: 없음

# 판단기준
- **정상**: 팀 상태가 정상이고 실패 멤버 수가 허용 범위 이내입니다.
- **대상 아님**: LBFO 기능 또는 팀 구성이 없는 일반 단일 NIC 환경입니다.
- **경고**: Down/Degraded 팀 또는 비정상 멤버 수가 임계치를 초과합니다.


