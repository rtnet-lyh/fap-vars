# 영역
NETWORK

# 세부 점검항목
이중화 구성 상태 점검

# 점검 내용
Failover 상태 확인

# 구분
권고

# 명령어
```text
show standby brief
show vrrp brief
```

# 출력 결과
```text
Interface   Grp  Pri P State    Active          Standby         Virtual IP
Vlan10      10   110 P Active   local           10.10.10.2      10.10.10.1

Interface  Grp Pri Time Own Pre State   Master addr      Group addr
Vlan20     20  110 1    Y   Y   Master  10.20.20.2       224.0.0.18
```

# 설명
- `show standby brief` 명령은 HSRP 기반 게이트웨이 이중화 상태를 확인하는 데 사용한다.
- `show vrrp brief` 명령은 VRRP 기반 이중화 환경에서 Master 또는 Backup 상태를 확인하는 데 사용한다.
- Active 또는 Master 역할이 정상적으로 선출되고, 상대 장비가 Standby 또는 Backup 상태로 대기하는지 확인해야 한다.
- Split-brain, Active 장비 부재, 상태 반복 전환이 보이면 이중화 링크, 우선순위, 추적 객체, 헬스체크 구성을 점검해야 한다.

# 임계치
없음

# 판단기준
- **양호**: 운영 중인 이중화 프로토콜에서 Active 또는 Master와 대기 장비 상태가 정상적으로 확인되는 경우
- **주의**: 이중화는 구성되어 있으나 상태 전환 이력이나 우선순위 불일치 등 추가 점검이 필요한 경우
- **경고**: Active 또는 Master 부재, 양측 Active 성격의 이상, 잦은 Failover가 확인되는 경우
- **확인 필요**: HSRP 또는 VRRP를 사용하지 않는 환경으로 적용 대상 여부 확인이 필요한 경우

