# 영역
NETWORK

# 세부 점검항목
라우팅 Table 상태

# 점검 내용
Static/OSPF/BGP 라우팅 Table 정상 여부 확인

# 구분
권고

# 명령어
```text
show ip route
show ip ospf neighbor
show ip bgp summary
```

# 출력 결과
```text
Gateway of last resort is 10.0.0.1 to network 0.0.0.0

O    10.10.20.0/24 [110/20] via 10.0.0.2, 00:00:17, GigabitEthernet0/0
B    172.16.0.0/16 [20/0] via 192.0.2.2, 00:00:45
S*   0.0.0.0/0 [1/0] via 10.0.0.1

Neighbor ID     Pri   State           Dead Time   Address         Interface
1.1.1.1           1   FULL/DR         00:00:33    10.0.0.2        Gi0/0

Neighbor        V    AS MsgRcvd MsgSent TblVer InQ OutQ Up/Down  State/PfxRcd
192.0.2.2       4 65001     125     119     48   0    0 2d03h           14
```

# 설명
- `show ip route` 명령은 기본 경로와 동적 또는 정적 라우트의 설치 상태를 확인하는 핵심 명령이다.
- `show ip ospf neighbor`, `show ip bgp summary` 명령은 동적 라우팅 프로토콜 사용 시 인접 관계와 수신 경로 수를 점검하는 데 사용한다.
- 기본 경로 누락, 주요 목적지 경로 부재, OSPF neighbor 비정상, BGP 세션 미수립 상태는 서비스 경로 단절의 주요 징후다.
- OSPF 또는 BGP를 사용하지 않는 환경에서는 해당 명령 결과가 없을 수 있으므로 실제 운영 프로토콜 기준으로 해석해야 한다.

# 임계치
없음

# 판단기준
- **양호**: 기본 경로와 주요 업무 경로가 존재하고, 사용 중인 동적 라우팅 프로토콜의 neighbor 또는 session 상태가 정상인 경우
- **주의**: 경로는 존재하지만 neighbor 재수립이 빈번하거나 수신 prefix 수 변동이 커서 추가 확인이 필요한 경우
- **경고**: 기본 경로 또는 핵심 업무 경로가 누락되거나 OSPF/BGP 인접 상태가 비정상인 경우
- **확인 필요**: OSPF/BGP를 사용하지 않는 환경으로 해당 명령 결과가 비어 있어 운영 프로토콜 기준 확인이 필요한 경우

