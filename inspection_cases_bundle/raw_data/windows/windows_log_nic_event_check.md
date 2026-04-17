# 영역
NETWORK

# 세부 점검 항목
NIC 상태 및 최근 NIC 이벤트 로그

# 점검 내용
현재 NIC 상태를 확인하고 최근 30일간 NIC 링크/미디어/failover 관련 이벤트를 함께 점검합니다.

# 구분
필수

# 명령어
```powershell
'==NIC Status=='; Get-NetAdapter -IncludeHidden -ErrorAction SilentlyContinue | Select-Object Name,InterfaceDescription,Status,LinkSpeed,MacAddress,ifIndex | Format-Table -Auto; '==Recent NIC Events=='; $e=Get-WinEvent -FilterHashtable @{LogName='System';StartTime=(Get-Date).AddDays(-30);Level=@(1,2,3)} -ErrorAction SilentlyContinue | Where-Object { $_.Message -match '(?i)\\bnic\\b|network adapter|link down|link up|media disconnected|media connected|status down|status up|failover' }; if($e){$e | Select-Object -First 50 TimeCreated,ProviderName,Id,LevelDisplayName,@{N='Message';E={($_.Message -replace '\\r?\\n',' ')}} | Format-Table -Wrap -Auto}else{'No NIC link/failover-like warning or error events found in the last 30 days.'}
```

# 출력 결과
```text
==NIC Status==
Name      InterfaceDescription           Status  LinkSpeed
Ethernet  Intel(R) Ethernet Controller   Up      1 Gbps

==Recent NIC Events==
No NIC link/failover-like warning or error events found in the last 30 days.
```

# 설명
- 서비스용 NIC 수와 최근 NIC 이벤트 수를 동시에 확인합니다.
- 가상 어댑터나 보조 인터페이스 일부는 서비스 NIC 판정에서 제외됩니다.

# 임계치
- `min_up_nic_count`: `1`
- `max_nic_event_count`: `0`
- `failure_keywords`: 없음

# 판단기준
- **정상**: 서비스 NIC 중 Up 상태인 인터페이스 수가 기준 이상이고 최근 이벤트도 허용 범위 이내입니다.
- **경고**: 활성 NIC 수 부족 또는 NIC 링크/장애조치 관련 이벤트가 임계치를 초과합니다.


