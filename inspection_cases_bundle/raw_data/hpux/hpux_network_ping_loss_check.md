# 영역
NETWORK

# 세부 점검항목
Ping Loss

# 점검 내용
Default Router 또는 지정 대상과의 네트워크 통신 상태를 점검한다.

# 구분
권고

# 명령어
```bash
ping 192.168.1.1 64 3
```

# 출력 결과
```text
PING 192.168.1.1: 64 byte packets
64 bytes from 192.168.1.1: icmp_seq=0. time=0.5 ms
64 bytes from 192.168.1.1: icmp_seq=1. time=0.4 ms
64 bytes from 192.168.1.1: icmp_seq=2. time=0.5 ms

----192.168.1.1 PING Statistics----
3 packets transmitted, 3 packets received, 0% packet loss
round-trip (ms)  min/avg/max = 0.4/0.5/0.5
```

# 설명
- 기본 게이트웨이 또는 운영 기준 대상 IP로 ICMP 통신 상태를 확인한다.
- packet loss가 발생하면 네트워크 경로, 스위치 포트, 라우팅, 방화벽, NIC 상태를 확인한다.
- 지연 시간이 높거나 변동 폭이 크면 네트워크 혼잡 또는 경로 장애 가능성이 있다.
- ICMP가 차단된 환경에서는 애플리케이션 포트 또는 별도 네트워크 점검 방식으로 대체한다.

# 임계치
PING_LOSS_MAX_PCT
PING_LATENCY_MAX_MS
PING_TARGET

# 판단기준
- **양호**: packet loss가 `PING_LOSS_MAX_PCT` 이하이고 평균 지연 시간이 기준 이하인 경우
- **경고**: packet loss 또는 평균 지연 시간이 임계치를 초과하는 경우
- **확인 필요**: ICMP 차단 또는 대상 IP 기준 미정으로 판단이 어려운 경우
