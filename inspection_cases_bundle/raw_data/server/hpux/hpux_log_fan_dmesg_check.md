# 영역
로그

# 세부 점검항목
FAN 로그

# 점검 내용
FAN 작동 이상 유무 점검(FAN Fail)

# 구분
필수

# 명령어
```bash
dmesg | egrep -i 'fan|over[- ]?temp|not spinning|failed'
```

# 출력 결과
```text
FAN failed: Over-temperature detected
```

# 설명
- `dmesg` 로그에서 FAN 장애, 회전 정지, 과열 관련 메시지를 확인한다.
- `fan operational`, `fan normal`처럼 정상 상태를 의미하는 메시지는 불량으로 보지 않는다.
- FAN 장애나 과열 로그가 있으면 장비 온도, 팬 모듈, 전원/랙 환경을 점검한다.
- 반복 발생 시 하드웨어 교체 또는 벤더 점검을 권고한다.

# 임계치
fan_bad_log_keywords
fan_ignore_log_keywords

# 판단기준
- **양호**: FAN 장애 또는 과열 로그가 없는 경우
- **경고**: FAN fail, failed, not spinning, over-temp 로그가 확인되는 경우
- **확인 필요**: 로그 접근 또는 장비 센서 상태 확인이 불가능한 경우
