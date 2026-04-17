# 영역
LOG

# 세부 점검 항목
HBA 관련 이벤트 로그

# 점검 내용
스토리지 HBA, FC, SAS, 미니포트 드라이버 관련 이벤트를 검색합니다.

# 구분
필수

# 명령어
```powershell
'==Initiator Ports=='; $ip=Get-InitiatorPort -ErrorAction SilentlyContinue; if($ip){$ip|Select-Object InstanceName,ConnectionType,NodeAddress,PortAddress|Format-Table -Auto}else{'No HBA initiator ports exposed.'}; '==FC Port State=='; $fc=Get-CimInstance -Namespace root\\wmi -Class MSFC_FibrePortHBAAttributes -ErrorAction SilentlyContinue; if($fc){$fc|Select-Object InstanceName,@{N='PortState';E={switch($_.Attributes.PortState){1{'Unknown'}2{'Operational'}3{'User Offline'}4{'Bypassed'}5{'Diagnostics'}6{'Link Down'}7{'Port Error'}8{'Loopback'}default{$_.Attributes.PortState}}}},HBAStatus|Format-Table -Auto}else{'No FC HBA port-state data exposed by driver.'}; '==Recent HBA Events=='; $ev=Get-WinEvent -FilterHashtable @{LogName='System';StartTime=(Get-Date).AddDays(-30);Level=@(1,2,3)} -ErrorAction SilentlyContinue|Where-Object{$_.Message -match '(?i)\\bhba\\b|fibre channel|fiber channel|\\bfc\\b|loopback|link down|port.+offline|port.+online'}; if($ev){$ev|Select-Object -First 50 TimeCreated,ProviderName,Id,LevelDisplayName,@{N='Message';E={($_.Message -replace '\\r?\\n',' ')}}|Format-Table -Wrap -Auto}else{'No HBA/port offline-online-like events found in the last 30 days.'}
```

# 출력 결과
```text
No HBA warning or error events found in the last 30 days.
```

# 설명
- HBA 드라이버 오류, 링크 문제, 스토리지 경로 문제를 이벤트 로그에서 확인합니다.
- HBA가 없는 일반 Windows 11 환경에서는 관련 이벤트가 없을 수 있습니다.

# 임계치
- `max_hba_event_count`: `0`
- `failure_keywords`: 없음

# 판단기준
- **정상**: HBA 관련 오류/경고 이벤트 수가 기준 이내입니다.
- **대상 아님**: HBA가 없는 환경이라 관련 로그가 없습니다.
- **경고**: HBA 관련 이벤트 수가 임계치를 초과합니다.


