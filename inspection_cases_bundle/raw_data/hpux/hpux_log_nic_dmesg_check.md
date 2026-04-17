# 영역
로그

# 세부 점검항목
NIC 로그

# 점검 내용
NIC 정상 유무 점검(Status Up/Down, Link Down, Failover)

# 구분
필수

# 명령어
```bash
dmesg | egrep -i 'link down|status down|failover|lan[0-9]+.*down|link up|status up'
```

# 출력 결과
```text
lan0: Link Down
```

# 설명
- `dmesg` 로그에서 NIC link down, status down, failover, lan 장치 down 메시지를 확인한다.
- `link up`, `status up` 메시지는 정상 또는 복구 상태로 간주한다.
- 링크 down 로그가 있으면 케이블, 스위치 포트, NIC 상태, APA 구성 상태를 함께 확인한다.
- failover 로그는 이중화 동작 여부와 원인 장비를 함께 점검한다.

# 임계치
nic_bad_log_keywords
nic_ignore_log_keywords

# 판단기준
- **양호**: NIC link/status down 또는 failover 장애 로그가 없는 경우
- **경고**: link down, status down, failover, lan down 로그가 확인되는 경우
- **확인 필요**: 로그 확인 또는 NIC 구성 정보 확인이 불가능한 경우
