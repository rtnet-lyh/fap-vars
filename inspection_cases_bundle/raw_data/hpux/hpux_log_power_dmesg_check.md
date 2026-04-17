# 영역
로그

# 세부 점검항목
POWER 로그

# 점검 내용
전원공급장치 오류 및 이상 유무 점검(PS Failed)

# 구분
필수

# 명령어
```bash
dmesg | egrep -i 'psu|power supply|power.*failed|not detected'
```

# 출력 결과
```text
(no output)
```

# 설명
- `dmesg` 로그에서 PSU, power supply, power failed, not detected 관련 메시지를 확인한다.
- 전원공급장치 장애 로그가 있으면 이중화 전원 구성, 전원 케이블, PDU, 장비 이벤트 로그를 확인한다.
- 단일 PSU 장애는 즉시 서비스 중단으로 이어지지 않더라도 이중화 위험 상태로 본다.
- 로그가 없으면 해당 키워드가 확인되지 않은 상태로 본다.

# 임계치
power_bad_log_keywords

# 판단기준
- **양호**: PSU 또는 전원 장애 로그가 없는 경우
- **경고**: PSU fail, power supply fail, power failed, not detected 로그가 확인되는 경우
- **확인 필요**: 로그 접근 또는 장비 전원 상태 확인이 불가능한 경우
