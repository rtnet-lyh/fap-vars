# 영역
NETWORK

# 세부 점검항목
통신 테스트

# 점검 내용
특정 장비와 통신상태를 확인함으로써 정상 통신 여부를 확인

# 구분
권고

# 명령어
```text
ping <ping_target> repeat <ping_count>
```

기본 임계치 기준 생성 예시:

```text
ping 192.0.2.10 repeat 10
```

# 출력 결과
```text
Type escape sequence to abort.
Sending 10, 100-byte ICMP Echos to 192.0.2.10, timeout is 2 seconds:
!!!!!!!!!!
Success rate is 100 percent (10/10), round-trip min/avg/max = 1/2/4 ms
```

# 설명
- Cisco IOS 장비에서는 `ping <ping_target> repeat <ping_count>` 명령으로 지정 대상과의 ICMP 통신 상태를 확인할 수 있다.
- `!`는 응답 성공, `.`는 타임아웃을 의미하며 결과 마지막 줄의 `Success rate`로 성공률을 판단한다.
- 게이트웨이, 상위 라우터, 핵심 서버, 원격 사이트 장비 등 운영상 의미 있는 대상을 지정해 통신 상태를 점검해야 한다.
- 손실률이 증가하거나 지연이 급증하면 회선 품질, ACL, 라우팅 경로, 이중화 전환 상태를 함께 점검한다.

# 임계치
ping_target
ping_count
max_ping_loss_percent

# 판단기준
- **양호**: `ping_target` 대상에 대해 `ping_count` 기준 점검 시 손실률이 `max_ping_loss_percent` 이하이고 응답이 안정적인 경우
- **주의**: 응답은 있으나 지연 편차가 크거나 손실률이 임계치에 근접한 경우
- **경고**: 손실률이 `max_ping_loss_percent`를 초과하거나 응답이 전혀 수신되지 않는 경우

