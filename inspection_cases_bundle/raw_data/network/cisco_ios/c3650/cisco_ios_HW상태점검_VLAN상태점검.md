# 영역
NETWORK

# 세부 점검항목
VLAN 상태 점검

# 점검 내용
VLAN 상태 및 Tagging 확인

# 구분
권고

# 명령어
```text
show vlan brief
show interfaces trunk
```

# 출력 결과
```text
VLAN Name                             Status    Ports
1    default                          active    Gi1/0/1, Gi1/0/2
10   SERVER                           active    Gi1/0/3, Gi1/0/4
20   DB                               active    Gi1/0/5, Gi1/0/6
999  NATIVE                           active

Port        Mode         Encapsulation  Status        Native vlan
Gi1/0/48    on           802.1q         trunking      999

Port        Vlans allowed on trunk
Gi1/0/48    10,20,30,999

Port        Vlans in spanning tree forwarding state and not pruned
Gi1/0/48    10,20,30,999
```

# 설명
- `show vlan brief` 명령은 VLAN 생성 상태와 액세스 포트 할당 상태를 확인하는 명령이다.
- `show interfaces trunk` 명령은 트렁크 포트의 802.1Q 태깅 상태, Native VLAN, 허용 VLAN 목록을 확인하는 데 사용한다.
- 운영에 필요한 VLAN이 `active` 상태인지, 기대한 포트에 정확히 매핑되어 있는지 확인해야 한다.
- 트렁크 포트의 허용 VLAN 목록이나 Native VLAN이 설계와 다르면 통신 불가, VLAN 누수, 이중화 경로 이상이 발생할 수 있다.

# 임계치
없음

# 판단기준
- **양호**: 필요한 VLAN이 모두 `active` 상태이고 액세스 및 트렁크 포트의 태깅 구성이 운영 기준과 일치하는 경우
- **주의**: VLAN은 존재하지만 일부 포트 매핑 또는 허용 VLAN 목록이 운영 기준과 일부 다른 경우
- **경고**: 필수 VLAN이 비활성 상태이거나 트렁크 포트가 비정상 상태이거나 Native VLAN 오설정이 확인되는 경우

