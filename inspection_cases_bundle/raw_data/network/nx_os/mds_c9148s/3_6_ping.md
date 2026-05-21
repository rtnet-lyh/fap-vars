# 영역
서비스

# 세부 점검항목
통신 테스트

# 점검 내용
특정 장비와 통신상태 정상 확인.

# 구분
권고

# 명령어
```bash
ping `ping_ip` count 5
```

# 출력 결과(성공)
```text
CITS-SAN1# ping 193.1.0.207 count 5
PING 193.1.0.207 (193.1.0.207) 56(84) bytes of data.
64 bytes from 193.1.0.207: icmp_seq=1 ttl=64 time=0.202 ms
64 bytes from 193.1.0.207: icmp_seq=2 ttl=64 time=0.195 ms
64 bytes from 193.1.0.207: icmp_seq=3 ttl=64 time=0.198 ms
64 bytes from 193.1.0.207: icmp_seq=4 ttl=64 time=0.196 ms
64 bytes from 193.1.0.207: icmp_seq=5 ttl=64 time=0.195 ms

--- 193.1.0.207 ping statistics ---
5 packets transmitted, 5 received, 0% packet loss, time 3996ms
rtt min/avg/max/mdev = 0.195/0.197/0.202/0.009 ms
```
# 출력 결과(실패)
```text
CITS-SAN1# ping 193.1.55.207 count 5
PING 193.1.55.207 (193.1.55.207) 56(84) bytes of data.
From 193.1.0.252 icmp_seq=1 Destination Host Unreachable
From 193.1.0.252 icmp_seq=2 Destination Host Unreachable
From 193.1.0.252 icmp_seq=3 Destination Host Unreachable
From 193.1.0.252 icmp_seq=4 Destination Host Unreachable
From 193.1.0.252 icmp_seq=5 Destination Host Unreachable

--- 193.1.55.207 ping statistics ---
5 packets transmitted, 0 received, +5 errors, 100% packet loss, time 4005ms
```

# 설명
- 명령어: 특정 대상 IP와 통신 가능여부를 5회 확인하는 명령어.
- received가 5면 정상 판단 가능
- 통신 확인 할 IP를 호스트 변수로 받아와야함.


# 임계치
ping_ip
- 통신확인 할 IP를 변수로 설정

# 판단기준
- **양호**: 결과 값 내 '5 received' 문자 포함
- **경고**: 결과 값 내 '5 received' 문자 미 포함
- **확인 필요**: 명령어 실패 및 `ping_ip` 변수 미 선언, 파싱 불가