# 영역
STORAGE

# 세부 점검 항목
OS 관점 HBA 링크 상태

# 점검 내용
스토리지 어댑터 포트 정보를 조회해 Online이 아닌 포트 수를 점검합니다.

# 구분
필수

# 명령어
```powershell
if (Get-CimClass -Namespace root\\WMI -ClassName MSFC_FibrePortHBAAttributes -ErrorAction SilentlyContinue) { Get-CimInstance -Namespace root\\WMI -ClassName MSFC_FibrePortHBAAttributes | Select-Object @{N='fc_portname';E={(($_.Attributes.PortWWN | ForEach-Object { '{0:X2}' -f $_ }) -join '')}}, @{N='fc_node_name';E={(($_.Attributes.NodeWWN | ForEach-Object { '{0:X2}' -f $_ }) -join '')}}, @{N='fc_state';E={switch ($_.Attributes.PortState) { 2 {'Online'} 3 {'Offline'} 6 {'Link Down'} 7 {'Error'} default { \"State:$($_.Attributes.PortState)\" } }}}, @{N='fc_speed';E={switch ($_.Attributes.PortSpeed) { 0 {'Unknown'} 1 {'1 Gbps'} 2 {'2 Gbps'} 4 {'10 Gbps'} 8 {'4 Gbps'} 9 {'Not Negotiated'} default { \"Raw:$($_.Attributes.PortSpeed)\" } }}} | Format-Table -AutoSize } else { 'FC HBA WMI class not found' }
```

# 출력 결과
```text
NodeWWN               PortWWN               PortState  PortType
10:00:00:00:00:00:00:01  20:00:00:00:00:00:00:01  Online     Fabric
```

# 설명
- FC/HBA 포트가 있는 환경에서 링크 상태를 직접 확인하는 항목입니다.
- 비스토리지 단말에서는 관련 어댑터가 없어 대상 아님처럼 해석될 수 있습니다.

# 임계치
- `max_non_online_port_count`: `0`
- `failure_keywords`: 없음

# 판단기준
- **정상**: Online이 아닌 포트 수가 허용 범위 이내입니다.
- **대상 아님**: HBA 어댑터가 없는 환경입니다.
- **경고**: 비정상 포트 수가 임계치를 초과합니다.


