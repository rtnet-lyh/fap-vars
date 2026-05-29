# 영역
이중화

# 세부 점검항목
Path 이중화 점검

# 점검 내용
Multipath 이중화 정상유무 점검 (Online 상태확인)

# 구분
필수

# 명령어
```bash
ifgroup show config all
```

# 출력 결과 (테스트 서버: 172.31.247.114)
```text
sysadmin@localhost# ifgroup show config all

Group-name   Status     Interface   Clients   Replication
----------   --------   ---------   -------   -----------
default      disabled           0         1             0
----------   --------   ---------   -------   -----------
No interfaces in ifgroup

Group-name   Status     DD Boost Clients
----------   --------   ----------------
default      disabled   *
----------   --------   ----------------
No replication mtrees with remote hosts in ifgroup
File replication is allowed on ifgroup.
Client may use any interface.

```

# 설명
- ifgroup show config all 명령어를 통해 네트워크 Path 이중화(ifgroup/Bonding) 구성 여부를 확인할 수 있음
- ifgroup은 여러 네트워크 인터페이스를 묶어 이중화 및 부하분산을 수행하는 기능임
- 인터페이스 장애 발생 시에도 통신 지속성을 유지하기 위해 구성됨
- Data Domain 장비에서 ifgroup 미구성 시 단일 인터페이스 기반으로 동작할 수 있음

# 임계치
min_ifgroup_interface_cnt: 1
ifgroup_status_keywords = [
    "disabled",
    "down",
    "offline",
    "fail",
    "error"
]

# 판단기준
- **양호**: 명령어 출력값에서 ifgroup 상태가 enable 상태이며, interface 수가 `min_ifgroup_interface_cnt`개 이상인 경우
- **경고**: 명령어 출력값에서 ifgroup 상태가 disabled 상태이거나, "No interfaces in ifgroup" 메시지가 존재하는 경우
- **확인 필요**: 명령어 수행 실패 또는 출력 결과를 확인할 수 없는 경우
