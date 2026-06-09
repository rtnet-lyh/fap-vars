# 영역
NETWORK

# 세부 점검항목
네트워크 인터페이스 사용률

# 점검 내용
네트워크 인터페이스 사용현황을 확인하여 네트워크 병목여부 확인

# 구분
필수

# 명령어
```text
show interfaces
```

# 출력 결과
```text
GigabitEthernet1/0/1 is up, line protocol is up
  Hardware is Gigabit Ethernet, address is 0011.2233.4455
  MTU 1500 bytes, BW 1000000 Kbit/sec, DLY 10 usec
  reliability 255/255, txload 32/255, rxload 28/255
  5 minute input rate 125000 bits/sec, 180 packets/sec
  5 minute output rate 98000 bits/sec, 150 packets/sec

TenGigabitEthernet1/1/1 is up, line protocol is up
  Hardware is Ten Gigabit Ethernet, address is 00aa.bbcc.ddee
  MTU 1500 bytes, BW 10000000 Kbit/sec, DLY 10 usec
  reliability 255/255, txload 201/255, rxload 198/255
  5 minute input rate 7780000000 bits/sec, 910000 packets/sec
  5 minute output rate 7560000000 bits/sec, 882000 packets/sec
```

# 설명
- `show interfaces` 명령은 인터페이스별 속도, 5분 평균 입출력 트래픽, load, 오류 통계를 함께 확인할 수 있는 기본 명령이다.
- `BW`는 인터페이스 대역폭 기준값이고, `5 minute input/output rate`는 최근 5분 평균 트래픽 사용량을 의미한다.
- `txload`, `rxload`는 255 기준의 상대 부하값이며, 이를 통해 인터페이스 포화 상태를 빠르게 파악할 수 있다.
- 사용률이 지속적으로 높으면 회선 증설, 트래픽 분산, QoS 정책, 이중화 경로 분산 상태를 함께 확인해야 한다.

# 임계치
max_interface_utilization_percent

# 판단기준
- **양호**: 주요 인터페이스의 입출력 사용률이 `max_interface_utilization_percent` 이하이고 포화 징후가 없는 경우
- **주의**: 단기적으로 사용률이 높지만 지속적 포화로 보이지 않거나 일부 인터페이스만 임계치에 근접한 경우
- **경고**: 주요 인터페이스의 평균 사용률이 `max_interface_utilization_percent`를 초과하여 병목 가능성이 있는 경우

