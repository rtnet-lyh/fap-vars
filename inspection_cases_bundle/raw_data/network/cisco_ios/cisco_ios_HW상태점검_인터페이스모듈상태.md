# 영역
NETWORK

# 세부 점검항목
인터페이스/모듈 상태

# 점검 내용
각 인터페이스/Module Down/up 상태 점검 및 CRC error 증가 여부 확인

# 구분
필수

# 명령어
```text
show interfaces
show inventory
```

# 출력 결과
```text
GigabitEthernet1/0/1 is up, line protocol is up
  0 input errors, 0 CRC, 0 frame, 0 overrun, 0 ignored
  0 output errors, 0 collisions, 0 interface resets

TenGigabitEthernet1/1/1 is down, line protocol is down
  12 input errors, 8 CRC, 0 frame, 0 overrun, 0 ignored
  0 output errors, 0 collisions, 3 interface resets

NAME: "Chassis", DESCR: "Cisco Catalyst 9300 Chassis"
PID: C9300-48P        , VID: V02  , SN: FJC1234A0BC
NAME: "Uplink Module 1", DESCR: "Catalyst 9300 8 x 10GE Network Module"
PID: C9300-NM-8X      , VID: V01  , SN: FDO5678D1EF
```

# 설명
- `show interfaces` 결과로 물리 인터페이스와 논리 프로토콜이 모두 `up`인지 확인하고, 오류 카운터 증가 여부를 함께 본다.
- `CRC`, `input errors`, `interface resets` 값이 증가하면 광모듈, 케이블, 포트, duplex 불일치, 회선 품질 문제 가능성이 있다.
- `show inventory` 명령은 장비와 모듈이 정상 인식되는지 확인하는 데 사용한다.
- 운영 대상 인터페이스가 `down/down` 이거나 모듈이 인식되지 않으면 서비스 영향 여부를 즉시 확인해야 한다.

# 임계치
max_crc_error_count

# 판단기준
- **양호**: 운영 대상 인터페이스가 `up/up` 상태이고 CRC 및 주요 오류 카운터가 `max_crc_error_count` 이하인 경우
- **주의**: 인터페이스는 `up/up` 상태지만 CRC 또는 입력 오류 카운터가 증가하고 있어 물리 구간 점검이 필요한 경우
- **경고**: 운영 대상 인터페이스가 `down` 상태이거나 CRC 오류가 `max_crc_error_count`를 초과하거나 필수 모듈이 인식되지 않는 경우

