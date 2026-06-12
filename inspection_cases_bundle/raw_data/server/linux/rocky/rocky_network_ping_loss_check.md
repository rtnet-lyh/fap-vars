# 영역
NETWORK

# 세부 점검항목
Ping Loss

# 점검 내용
Network 통신 상태 점검(Default Router로 Ping 테스트)

# 구분
권고

# 명령어
```bash
ping -c <ping_count> <ping_target>
```

기본 임계치 기준 생성 예시:

```bash
ping -c 10 8.8.8.8
```

# 출력 결과
```text
64 bytes from 8.8.8.8: icmp_seq=1 ttl=111 time=38.8 ms
10 packets transmitted, 10 received, 0% packet loss
rtt min/avg/max/mdev = 38.3/39.6/40.6/0.7 ms
```

# 설명
- 본 항목은 `ping_count`, `ping_target` 임계치 값을 이용해 `ping -c <ping_count> <ping_target>` 명령을 동적으로 구성하여 네트워크 통신 상태를 점검한다.
- 기본 임계치 예시인 `ping_count=10`, `ping_target=8.8.8.8` 기준에서는 외부 대상과의 네트워크 통신 가능 여부와 패킷 손실률, RTT 응답 시간을 함께 확인한다.
- `64 bytes from 8.8.8.8`는 대상 시스템으로부터 ICMP Echo Reply를 정상적으로 수신했음을 의미한다.
- `icmp_seq`는 패킷 순번, `ttl`은 패킷이 통과 가능한 홉 수, `time`은 각 패킷의 응답 시간을 의미한다.
- 예시 출력의 `10 packets transmitted, 10 received, 0% packet loss`는 전송한 10개 패킷이 모두 정상 수신되어 손실률이 0%임을 나타낸다.
- `rtt min/avg/max/mdev`는 최소, 평균, 최대 응답 시간과 편차를 보여준다. 손실률 증가나 응답 시간 급증이 보이면 라우터, 회선, 방화벽, NIC 상태를 함께 점검한다.

# 임계치
ping_count: 10
ping_target: 8.8.8.8
max_ping_loss_percent: 0

# 판단기준
- **양호**: `ping_target` 대상에 대해 `ping_count` 횟수 기준으로 점검했을 때 패킷 손실률이 `max_ping_loss_percent` 이하이고 응답이 정상 수신되는 경우
- **경고**: `ping_target` 대상에 대해 `ping_count` 횟수 기준으로 점검했을 때 패킷 손실률이 `max_ping_loss_percent`를 초과하거나 응답이 전혀 수신되지 않는 경우
- **참고**: 실제 운영 환경에서는 `8.8.8.8` 대신 기본 게이트웨이 또는 내부 라우터 IP로 대체해 점검할 수 있다
