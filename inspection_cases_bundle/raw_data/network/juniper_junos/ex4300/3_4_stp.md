# 영역
서비스

# 세부 점검항목
STP 상태 점검

# 점검 내용
STP 설정을 통해 Loop 구조를 방지하고 원활한 통신상태를 확인

# 구분
권고

# 명령어
```bash
show spannig-tree
```

# 출력 결과
```text
falcon@Center_Server_J4300_B> show spanning-tree interface

Spanning tree interface parameters for instance 0

Interface                  Port ID    Designated         Designated         Port    State  Role
                                       port ID           bridge ID          Cost
ge-0/0/28                  128:490      128:490   8192.c8fe6a91c080        20000    FWD    DESG
ge-0/0/29                  128:491      128:491   8192.c8fe6a91c080        20000    FWD    DESG
xe-0/0/35                  128:492      128:494   4096.f4bfa8edae40         2000    FWD    ROOT

```

# 설명
- 명령어: 장비의 STP 인터페이스별 상태를 확인하는 명령어.
- State: STP 포트의 현재 전달 상태를 의미.
    - FWD: Forwarding 상태로, 트래픽을 정상 전달하는 상태.
    - BLK, DSC: Loop 방지를 위해 트래픽 전달을 차단하는 상태.

- Role: STP에서 해당 포트가 수행하는 역할을 의미.
    - ROOT: Root Bridge 방향으로 선택된 Root port를 의미.
    - DESG: Designated port로, 해당 세그먼트에서 트래픽을 전달하는 정상포트
    - ALT: Root Port 장애 시 대체 경로, 평상시에는 Loop 방지를 위해 차단 상태 일 수 있음.

[정상 State/Role 조합]
State  Role     설명
FWD     DESG     Designated 정상 전달 포트
FWD     ROOT     Root Bridge 방향 정상 전달 포트
BLK     ALT      Loop 방지를 위해 차단된 대체 포트
DSC     ALT      Loop 방지를 위해 차단된 대체 포트

[참고]
AI를 통해 수집한 정상 조합임. 실제와 다를 수 있음

# 임계치


# 판단기준
- **양호**: 정상 State/Role 조합인 경우.
- **경고**: 정상 State/Role 조합이 아닌 경우.
- **확인 필요**: 명령어 실패 및 파싱 불가