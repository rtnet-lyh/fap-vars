# 영역
NETWORK

# 세부 점검항목
STP 상태 점검

# 점검 내용
STP 설정을 통해 Loop구조를 방지하고 원활한 통신상태를 확인

# 구분
권고

# 명령어
```text
show spanning-tree summary
show spanning-tree inconsistentports
```

# 출력 결과
```text
Switch is in rapid-pvst mode
Root bridge for: VLAN0010, VLAN0020, VLAN0030
PortFast Default is disabled
PortFast BPDU Guard Default is enabled
Loopguard Default is enabled
Number of topology changes 4 last change occurred 00:12:14 ago

Name                 Interface             Inconsistency
-------------------- --------------------- ------------------
No inconsistent ports found
```

# 설명
- `show spanning-tree summary` 명령은 STP 동작 모드, Root Bridge 상태, 기본 보호 기능, 토폴로지 변경 횟수를 확인한다.
- `show spanning-tree inconsistentports` 명령은 루프 방지 기능에 의해 차단된 포트가 있는지 확인하는 데 사용한다.
- 토폴로지 변경이 과도하게 증가하거나 inconsistent port가 발생하면 루프, BPDU Guard, Root Guard, 링크 불안정 문제를 의심해야 한다.
- 액세스 스위치와 배포 스위치의 역할에 따라 Root Bridge 위치가 설계와 일치하는지도 함께 점검한다.

# 임계치
없음

# 판단기준
- **양호**: STP 모드와 Root Bridge 상태가 설계와 일치하고 inconsistent port가 없는 경우
- **주의**: 토폴로지 변경이 잦거나 일부 보호 기능 상태를 추가 확인해야 하는 경우
- **경고**: inconsistent port가 존재하거나 Root Bridge 위치가 비정상적이거나 루프 징후가 확인되는 경우

