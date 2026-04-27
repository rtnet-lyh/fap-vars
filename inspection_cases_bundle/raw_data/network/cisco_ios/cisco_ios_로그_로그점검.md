# 영역
NETWORK

# 세부 점검항목
로그 점검

# 점검 내용
HW 상태와 관련된 Error 로그(Fail, Error, Warning, Stop, Down) 발생 유무 점검

# 구분
필수

# 명령어
```text
show logging
show logging | include FAIL|ERROR|WARNING|STOP|DOWN
```

# 출력 결과
```text
Syslog logging: enabled (0 messages dropped, 0 flushes, 0 overruns)
Console logging: level debugging, 287 messages logged

%LINK-3-UPDOWN: Interface GigabitEthernet1/0/48, changed state to down
%LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet1/0/48, changed state to down
%PM-4-ERR_DISABLE: bpduguard error detected on Gi1/0/24, putting Gi1/0/24 in err-disable state
%SYS-5-CONFIG_I: Configured from console by admin on vty0
```

# 설명
- `show logging` 명령은 장비에 저장된 시스템 및 하드웨어 관련 로그를 점검하는 기본 명령이다.
- `include` 필터를 사용하면 `FAIL`, `ERROR`, `WARNING`, `STOP`, `DOWN` 같은 주요 장애 키워드를 빠르게 추려 확인할 수 있다.
- 인터페이스 down, err-disable, 모듈 장애, 전원 이상, 환경 경보와 같은 반복 로그는 실제 장애 또는 잠재 장애의 선행 징후일 수 있다.
- 정보성 로그와 실제 오류 로그를 구분해 해석해야 하며, 동일 메시지가 반복될 경우 최근 발생 시각과 관련 포트를 함께 확인해야 한다.

# 임계치
critical_log_keywords
warning_log_keywords

# 판단기준
- **양호**: 임계치에 정의된 치명적 오류 로그가 없고 경고성 로그도 반복적으로 발생하지 않는 경우
- **주의**: 경고 키워드에 해당하는 로그가 산발적으로 존재하거나 일시적 링크 flap 흔적이 있는 경우
- **경고**: 치명적 오류 로그가 존재하거나 동일 장애 로그가 반복적으로 발생하여 서비스 영향이 우려되는 경우

