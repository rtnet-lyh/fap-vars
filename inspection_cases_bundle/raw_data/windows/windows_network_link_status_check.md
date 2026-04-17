# 영역
NETWORK

# 세부 점검 항목
물리 NIC 링크 상태

# 점검 내용
Get-NetAdapter 결과를 기준으로 물리 NIC의 링크 Up 상태 개수를 점검합니다.

# 구분
필수

# 명령어
```powershell
Get-NetAdapter -Physical | Select-Object Name, InterfaceDescription, Status, LinkSpeed | Format-Table -AutoSize
```

# 출력 결과
```text
Name      InterfaceDescription              Status  LinkSpeed
Ethernet  Intel(R) Ethernet Controller     Up      1 Gbps
```

# 설명
- 가상/터널류 어댑터를 제외하고 실제 서비스용 물리 NIC의 링크 상태를 확인합니다.
- 최소 Up NIC 수를 기준으로 네트워크 연결성을 평가합니다.

# 임계치
- `min_up_physical_nic_count`: `1`
- `failure_keywords`: 없음

# 판단기준
- **정상**: Up 상태인 물리 NIC 수가 최소 기준 이상입니다.
- **경고**: 활성 물리 NIC 수가 기준보다 적습니다.


