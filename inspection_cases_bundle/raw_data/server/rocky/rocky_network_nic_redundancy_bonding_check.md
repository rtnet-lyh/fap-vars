# 영역
NETWORK

# 세부 점검항목
NIC 이중화 점검

# 점검 내용
시스템에 구성된 NIC bonding 인터페이스의 이중화 상태 점검(MII Status 및 Slave Interface 상태 확인)

# 구분
권고

# 명령어
```bash
if ls /proc/net/bonding/* >/dev/null 2>&1; then
  for b in /proc/net/bonding/*; do
    echo "===== $(basename "$b") ====="
    cat "$b"
  done
else
  echo "NIC BONDING NOT CONFIGURED"
fi
```

# 출력 결과
```text
===== bond0 =====
Ethernet Channel Bonding Driver: v3.7.1 (April 27, 2011)

Bonding Mode: fault-tolerance (active-backup)
Primary Slave: eth0 (primary_reselect always)
Currently Active Slave: eth1
MII Status: up

Slave Interface: eth0
MII Status: down
Speed: 1000 Mbps
Duplex: full
Link Failure Count: 1

Slave Interface: eth1
MII Status: up
Speed: 1000 Mbps
Duplex: full
Link Failure Count: 0

----- bonding 미구성 시 -----
NIC BONDING NOT CONFIGURED
```

# 설명
- `/proc/net/bonding/` 아래 파일은 Linux bonding 인터페이스 상태를 보여준다. 본 명령은 시스템에 구성된 bonding 인터페이스를 모두 찾아 순회 점검한다.
- bonding 인터페이스가 하나 이상 있으면 `===== bond0 =====` 같은 헤더와 함께 각 bonding 상태를 출력한다. bonding 파일이 하나도 없으면 `NIC BONDING NOT CONFIGURED` 문자열을 출력한다.
- `Bonding Mode`는 bonding 구성 방식을, bonding 레벨 `MII Status`는 해당 본드 인터페이스 자체의 링크 상태를 나타낸다. `MII Status: up`이면 해당 bonding 인터페이스가 연결 상태로 본다.
- 각 `Slave Interface` 블록의 `MII Status`는 bonding 구성원 NIC의 개별 상태를 나타낸다. 구성원 NIC가 모두 `up`이면 정상 이중화 상태이고, 하나라도 `down`이면 구성원 이상으로 경고 판단한다.
- 여러 bonding 인터페이스가 있을 경우 전체 결과는 실패가 하나라도 있으면 실패, 실패는 없고 경고가 하나라도 있으면 경고, 모든 bonding이 정상일 때만 성공으로 집계한다.

# 임계치
없음

# 판단기준
- **성공**: bonding 인터페이스가 하나 이상 구성되어 있고, 각 bonding의 레벨 `MII Status`가 `up`이며 모든 `Slave Interface`가 `up` 상태인 경우
- **경고**: bonding 인터페이스는 구성되어 있고 bonding 레벨 `MII Status`는 `up`이지만, 해당 bonding의 구성원 `Slave Interface` 중 하나 이상이 `down` 상태인 경우
- **실패**: bonding 인터페이스가 구성되어 있으나 bonding 레벨 `MII Status`가 `down`인 경우
- **실패**: 명령 결과가 `NIC BONDING NOT CONFIGURED`로 출력되어 시스템에 NIC bonding이 구성되어 있지 않은 경우
- **참고**: 예시 사유는 `NIC Bonding 미구성` 또는 `bond0 MII Status down`처럼 NIC bonding 기준으로 작성하고, HBA 관련 문구는 사용하지 않는다
