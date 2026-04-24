# 영역
NETWORK

# 세부 점검 항목
NIC 상태 및 최근 NIC 이벤트 로그

# 점검 내용
현재 NIC 상태를 확인하고 최근 30일간 NIC 링크/미디어 disconnected, failover, adapter reset 관련 이벤트를 함께 점검합니다.

# 구분
필수

# 명령어
```powershell
$OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); $nic=Get-NetAdapter -IncludeHidden -ErrorAction SilentlyContinue | Select-Object Name,InterfaceDescription,Status,LinkSpeed,MacAddress,ifIndex; $events=Get-WinEvent -FilterHashtable @{LogName='System';StartTime=(Get-Date).AddDays(-30);Level=@(1,2,3)} -ErrorAction SilentlyContinue | Where-Object { $_.ProviderName -match '(?i)ndis|netwtw|e1d|e1iexpress|e1rexpress|b57nd60a|bnx|mlx|netadaptercx|tcpip' -or $_.Message -match '(?i)\bnic\b|network adapter|link down|link up|media disconnected|media connected|network link is disconnected|network link has been established|disconnected from the network|connected to the network|adapter reset|network interface.*down|network interface.*up|status down|status up|failover' } | Sort-Object TimeCreated -Descending | Select-Object -First 50 @{N='TimeCreated';E={$_.TimeCreated.ToString('yyyy-MM-dd HH:mm:ss')}},ProviderName,Id,LevelDisplayName,@{N='Message';E={($_.Message -replace '\r?\n',' ')}}; $payload=[pscustomobject]@{NicStatus=@($nic);RecentEvents=@($events)}; $payload | ConvertTo-Json -Depth 5 -Compress
```

# 출력 결과
```json
{"NicStatus": [{"Name": "Ethernet", "InterfaceDescription": "Intel(R) Ethernet Controller", "Status": "Up", "LinkSpeed": "1 Gbps", "MacAddress": "00-11-22-33-44-55", "ifIndex": 1}], "RecentEvents": []}
```

# 설명
- 서비스용 NIC 수와 최근 NIC 이벤트 수를 동시에 확인합니다.
- 가상 어댑터나 보조 인터페이스 일부는 서비스 NIC 판정에서 제외됩니다.
- `link down`, `media disconnected`, `failover`, `adapter reset`은 장애성 이벤트로 보고, `link up`, `media connected`, `status up`은 참고용 양호 이벤트로 구분합니다.

# 임계치
- `min_up_nic_count`: `1`
- `max_nic_event_count`: `0`
- `failure_keywords`: 없음

# 판단기준
- **정상**: 서비스 NIC 중 Up 상태인 인터페이스 수가 기준 이상이고 최근 장애성 NIC 이벤트가 허용 범위 이내입니다.
- **경고**: 활성 NIC 수 부족 또는 `link down`/`media disconnected`/`failover`/`adapter reset` 이벤트가 임계치를 초과합니다.
