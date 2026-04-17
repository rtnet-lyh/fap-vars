# 영역
NETWORK

# 세부 점검항목
NW 링크 상태 연결속도 설정

# 점검 내용
Windows 네트워크 어댑터 링크 상태와 속도 확인

# 구분
필수

# 명령어
```powershell
$ErrorActionPreference = 'Stop'; $adapters = Get-NetAdapter | Select-Object Name, InterfaceDescription, Status, LinkSpeed, MacAddress; $down = @($adapters | Where-Object { $_.Status -ne 'Up' }); [pscustomobject]@{ adapter_count = @($adapters).Count; down_adapter_count = @($down).Count; adapters = $adapters } | ConvertTo-Json -Compress -Depth 6
```

# 출력 결과
```json
{"adapter_count":1,"down_adapter_count":0,"adapters":[{"Name":"Ethernet","InterfaceDescription":"Demo NIC","Status":"Up","LinkSpeed":"1 Gbps","MacAddress":"00-11-22-33-44-55"}]}
```

# 설명
- Get-NetAdapter로 네트워크 어댑터 링크 상태, 속도, MAC 주소를 확인한다.
- Down 상태 어댑터가 있으면 케이블, 스위치 포트, 드라이버, Teaming 구성을 추가 확인한다.

# 임계치
없음

# 판단기준
- **양호**: 네트워크 어댑터가 확인되고 Down 상태 어댑터가 없는 경우
- **주의**: Down 상태 어댑터가 하나 이상 확인되는 경우
- **경고**: 네트워크 어댑터가 확인되지 않는 경우
