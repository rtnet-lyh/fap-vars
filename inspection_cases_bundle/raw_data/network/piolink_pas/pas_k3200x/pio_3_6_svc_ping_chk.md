# 영역
서비스  

# 세부 점검항목
통신 테스트

# 점검 내용
특정 장비와 통신상태를 확인함으로써 정상 통신 여부를 확인

# 구분
권고

# 명령어 (변수: ip_address) count옵션 x 
```bash
ping {{ ip_address }}
```

# 출력 결과 (테스트 서버: 172.31.247.114)
```text
Center_PAS-K3200X_A# ping 172.31.247.114
PING 172.31.247.114 (172.31.247.114) 56(84) bytes of data.
64 bytes from 172.31.247.114: icmp_req=1 ttl=64 time=0.022 ms
64 bytes from 172.31.247.114: icmp_req=2 ttl=64 time=0.012 ms
^C
--- 172.31.247.114 ping statistics ---
2 packets transmitted, 2 received, 0% packet loss, time 999ms
rtt min/avg/max/mdev = 0.012/0.017/0.022/0.005 ms
Done
```

# 설명
- 응답 성공률(Success rate)은 ICMP 패킷 성공률을 의미하며 100%에 가까울수록 정상 상태를 의미 
- 최소/평균/최대 응답 시간(min/avg/max)은 패킷 왕복 시간(RTT)을 의미함

# 임계치
max_packet_loss_percent = 0 
max_avg_response_time_ms = 100 


# 판단기준
- **양호**: packet loss 값이 `max_packet_loss_percent` 이하이며 평균 응답 시간(avg)이 `max_avg_response_time_ms` 이하인 경우 
- **경고**: packet loss 값이 `max_packet_loss_percent` 초과 또는 평균 응답 시간(avg)이 `max_avg_response_time_ms` 초과인 경우
- **확인 필요**: 명령어 수행 실패 또는 출력 결과를 확인할 수 없는 경우
