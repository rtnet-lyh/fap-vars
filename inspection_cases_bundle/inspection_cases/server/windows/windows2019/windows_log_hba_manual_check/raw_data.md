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
$OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); $ip=Get-InitiatorPort -ErrorAction SilentlyContinue; $fc=Get-CimInstance -Namespace root\wmi -Class MSFC_FibrePortHBAAttributes -ErrorAction SilentlyContinue; $ev=Get-WinEvent -FilterHashtable @{LogName='System';StartTime=(Get-Date).AddDays(-30);Level=@(1,2,3)} -ErrorAction SilentlyContinue|Where-Object{$_.Message -match '(?i)\bhba\b|fibre channel|fiber channel|\bfc\b|loopback|link down|port.+offline|port.+online'}; $result=[ordered]@{InitiatorPortsExposed=[bool]$ip; FcPortStateExposed=[bool]$fc; EventDataExposed=[bool]$ev; InitiatorPorts=@($ip|Select-Object InstanceName,ConnectionType,NodeAddress,PortAddress); FcPorts=@($fc|Select-Object InstanceName,@{N='PortState';E={switch($_.Attributes.PortState){1{'Unknown'}2{'Operational'}3{'User Offline'}4{'Bypassed'}5{'Diagnostics'}6{'Link Down'}7{'Port Error'}8{'Loopback'}default{$_.Attributes.PortState}}}},HBAStatus); Events=@($ev|Select-Object -First 50 TimeCreated,ProviderName,Id,LevelDisplayName,@{N='Message';E={($_.Message -replace '\r?\n',' ')}})}; $result|ConvertTo-Json -Depth 4
```

# 출력 결과
```json
{
  "InitiatorPortsExposed": true,
  "FcPortStateExposed": true,
  "EventDataExposed": false,
  "InitiatorPorts": [
    {
      "InstanceName": "PORT0",
      "ConnectionType": "Fibre Channel",
      "NodeAddress": "20000090FA5376EC",
      "PortAddress": "10000090FA5376EC"
    }
  ],
  "FcPorts": [
    {
      "InstanceName": "PORT0",
      "PortState": "Operational",
      "HBAStatus": "OK"
    }
  ],
  "Events": []
}
```

# 설명
- HBA 드라이버 오류, 링크 문제, 스토리지 경로 문제를 이벤트 로그에서 확인합니다.
- HBA initiator 또는 FC 포트 상태 정보가 노출되지 않으면 점검 실패로 처리합니다.

# 임계치
- `max_hba_event_count`: `0`
- `failure_keywords`: 없음

# 판단기준
- **정상**: HBA 포트 상태 정보가 정상적으로 확인되고 HBA 관련 오류/경고 이벤트 수가 기준 이내입니다.
- **불량**: HBA initiator 또는 FC 포트 상태 정보를 확인할 수 없거나, HBA 관련 이벤트 수가 임계치를 초과합니다.


