# 영역
NETWORK

# 세부 점검항목
NW 링크 상태 연결속도 설정

# 점검 내용
Network 연결상태 정상 유무 점검(NIC 별 STATE Up, Down, Unknown 상태 확인)

# 구분
필수

# 명령어
```bash
ip link
```

# 출력 결과
```text
1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN mode DEFAULT group default qlen 1000
    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
258: br-b687e047b713: <NO-CARRIER,BROADCAST,MULTICAST,UP> mtu 1500 qdisc noqueue state DOWN mode DEFAULT group default 
    link/ether 0a:a9:67:08:33:43 brd ff:ff:ff:ff:ff:ff
2: eno1: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc mq state UP mode DEFAULT group default qlen 1000
    link/ether 74:9d:8f:0e:ad:f2 brd ff:ff:ff:ff:ff:ff
    altname enp2s0f0
3: eno2: <NO-CARRIER,BROADCAST,MULTICAST,UP> mtu 1500 qdisc mq state DOWN mode DEFAULT group default qlen 1000
    link/ether 74:9d:8f:0e:ad:f3 brd ff:ff:ff:ff:ff:ff
    altname enp2s0f1
4: enp129s0f0: <NO-CARRIER,BROADCAST,MULTICAST,UP> mtu 1500 qdisc mq state DOWN mode DEFAULT group default qlen 1000
    link/ether 04:27:58:0a:fa:2b brd ff:ff:ff:ff:ff:ff
5: enp129s0f1: <NO-CARRIER,BROADCAST,MULTICAST,UP> mtu 1500 qdisc mq state DOWN mode DEFAULT group default qlen 1000
    link/ether 04:27:58:0a:fa:2c brd ff:ff:ff:ff:ff:ff
6: br-3e40457894eb: <NO-CARRIER,BROADCAST,MULTICAST,UP> mtu 1500 qdisc noqueue state DOWN mode DEFAULT group default 
    link/ether 22:e6:03:db:9a:72 brd ff:ff:ff:ff:ff:ff
7: docker0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue state UP mode DEFAULT group default 
    link/ether 06:51:8e:96:c4:5d brd ff:ff:ff:ff:ff:ff
8: br-6a04ef950573: <NO-CARRIER,BROADCAST,MULTICAST,UP> mtu 1500 qdisc noqueue state DOWN mode DEFAULT group default 
    link/ether 36:03:8e:67:89:f5 brd ff:ff:ff:ff:ff:ff
524: veth32719e4@if2: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue master br-c05f4f389f6a state UP mode DEFAULT group default 
    link/ether 76:1d:6c:77:8b:c5 brd ff:ff:ff:ff:ff:ff link-netnsid 1
525: veth6291e48@if2: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue master br-c05f4f389f6a state UP mode DEFAULT group default 
    link/ether 92:74:f7:f8:cd:4e brd ff:ff:ff:ff:ff:ff link-netnsid 2
14: br-ed17885ef5c2: <NO-CARRIER,BROADCAST,MULTICAST,UP> mtu 1500 qdisc noqueue state DOWN mode DEFAULT group default 
    link/ether ca:ef:a5:bf:46:55 brd ff:ff:ff:ff:ff:ff
280: docker_gwbridge: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue state UP mode DEFAULT group default 
    link/ether 6e:ca:bc:88:d8:29 brd ff:ff:ff:ff:ff:ff
282: veth93dbdec@if281: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue master docker_gwbridge state UP mode DEFAULT group default 
    link/ether c2:9d:8b:c2:cb:b5 brd ff:ff:ff:ff:ff:ff link-netnsid 5
293: vethda7d78b@if292: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue master docker_gwbridge state UP mode DEFAULT group default 
    link/ether 5e:0c:cd:47:0e:7d brd ff:ff:ff:ff:ff:ff link-netnsid 8
294: vethe9072c6@if2: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue master docker0 state UP mode DEFAULT group default 
    link/ether 26:3a:00:00:e5:90 brd ff:ff:ff:ff:ff:ff link-netnsid 9
416: br-c05f4f389f6a: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue state UP mode DEFAULT group default 
    link/ether 22:a7:a5:36:a0:0c brd ff:ff:ff:ff:ff:ff
417: veth73eb6b0@if2: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue master br-c05f4f389f6a state UP mode DEFAULT group default 
    link/ether 86:8c:33:38:1d:df brd ff:ff:ff:ff:ff:ff link-netnsid 0
```

# 설명
- `ip link` 명령은 시스템에 인식된 네트워크 인터페이스와 링크 상태를 확인하는 기본 명령이다.
- `lo`는 루프백 인터페이스이며 `<LOOPBACK,UP,LOWER_UP>`로 표시되면 로컬 TCP/IP 스택이 정상 활성화된 상태로 본다.
- `ens33` 같은 물리 NIC가 `<BROADCAST,MULTICAST,UP,LOWER_UP>`로 표시되면 인터페이스가 활성 상태이고 링크도 정상 연결된 것으로 해석한다.
- `mtu 65536`은 루프백 인터페이스의 최대 전송 단위이고, `mtu 1500`은 일반적인 이더넷 인터페이스의 표준 MTU 값이다.
- 물리 NIC가 `DOWN` 또는 `NO-CARRIER` 상태이거나 기대한 인터페이스가 보이지 않으면 케이블, 스위치 포트, NIC 드라이버, OS 네트워크 설정을 점검한다.

# 임계치
- 제외할 인터페이스명 패턴
    - 예시: ^br-.*|^vethe.*|^docker.*

# 판단기준
- **양호**: 점검 대상 물리 NIC가 `UP`, `LOWER_UP` 상태로 확인되는 경우
- **주의**: 인터페이스 상태가 `UNKNOWN`이거나 기대한 NIC 이름과 실제 NIC 이름이 달라 추가 확인이 필요한 경우
- **경고**: 점검 대상 물리 NIC가 `DOWN`, `NO-CARRIER` 또는 비활성 상태로 확인되는 경우
