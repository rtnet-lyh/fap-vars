## ⑦-3 Ping Loss
- **영역(area)**: network
- **점검 항목**: Network 통신 상태 점검
- **명령어**:

```bash
ping 8.8.8.8
```

- **출력값**:

```text
PING 8.8.8.8: 56 data bytes
64 bytes from 8.8.8.8: icmp_seq=0 ttl=118 time=15.4 ms
64 bytes from 8.8.8.8: icmp_seq=1 ttl=118 time=14.6 ms
64 bytes from 8.8.8.8: icmp_seq=2 ttl=118 time=15.2 ms
64 bytes from 8.8.8.8: icmp_seq=3 ttl=118 time=15.3 ms
--- 8.8.8.8 ping statistics ---
4 packets transmitted, 4 received, 0% packet loss
round-trip (ms) min/avg/max = 14.6/15.1/15.4
```

- **설명**:
  - 평균 응답시간이 15.1ms 수준으로 양호한 예시.
  - 패킷 손실률 0%이면 네트워크가 안정적이라고 판단 가능.
  - RTT 최소/평균/최대값을 함께 확인.
