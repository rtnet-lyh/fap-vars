# 영역
NETWORK

# 세부 점검항목
Mac/Arp Table 상태 확인

# 점검 내용
Mac/Arp Table 정상 여부 확인

# 구분
권고

# 명령어
```text
show mac address-table dynamic
show ip arp
```

# 출력 결과
```text
          Mac Address Table
-------------------------------------------
Vlan    Mac Address       Type        Ports
----    -----------       --------    -----
  10    0011.2233.4455    DYNAMIC     Gi1/0/3
  20    aabb.ccdd.eeff    DYNAMIC     Gi1/0/5

Protocol  Address          Age (min)  Hardware Addr   Type   Interface
Internet  10.10.10.1               2  0011.2233.4455  ARPA   Vlan10
Internet  10.20.20.21              0  aabb.ccdd.eeff  ARPA   Vlan20
```

# 설명
- `show mac address-table dynamic` 명령은 스위치가 학습한 동적 MAC 주소와 포트 매핑 상태를 확인한다.
- `show ip arp` 명령은 IP와 MAC 매핑, VLAN 인터페이스 기준 ARP 학습 상태를 확인하는 데 사용한다.
- 운영상 필요한 서버, 게이트웨이, 상위 장비의 MAC 및 ARP 정보가 정상적으로 학습되는지 확인해야 한다.
- MAC 주소가 비정상적으로 이동하거나 ARP 항목이 누락되면 루프, 포트 이동, L2/L3 경계 이상, 게이트웨이 장애 가능성을 점검해야 한다.

# 임계치
없음

# 판단기준
- **양호**: 운영에 필요한 주요 MAC 및 ARP 항목이 정상적으로 학습되고 포트 매핑이 기대와 일치하는 경우
- **주의**: 일부 항목의 Age 변화가 비정상적이거나 포트 이동, Incomplete 성격의 이상 징후가 있는 경우
- **경고**: 필수 MAC 또는 ARP 항목이 학습되지 않거나 중복 학습, 비정상 플래핑이 확인되는 경우

