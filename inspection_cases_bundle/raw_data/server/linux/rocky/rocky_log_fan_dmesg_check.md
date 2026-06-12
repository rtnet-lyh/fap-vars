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
dmesg | grep -Ei 'fan|fan fail'
```

# 출력 결과
```text
[   10.234567] ipmi_si dmi-ipmi-si.0: Fan1 RPM lower critical - going low
[   10.235104] ipmi_si dmi-ipmi-si.0: Fan2 RPM lower non-recoverable - fan fail
[   10.235882] hwmon hwmon2: fan1 input not responding
[   10.236451] platform sensor_fan: cooling fan failure detected
[   10.237018] systemd[1]: Warning: chassis fan status is critical
```

# 설명
- (팬 오류 메시지) fan 또는 fan fail 메시지가 발견되면, 냉각 장치 이상 또는 회전수 저하가 발생했을 가능성이 있으므로 하드웨어 점검이 필요
- (회전수 임계치 메시지) RPM lower critical, non-recoverable 메시지가 확인되면 팬 속도가 임계치 이하로 떨어진 상태이므로 즉시 점검 권고
- (팬 응답 이상) fan input not responding 메시지가 발견되면 팬 센서 또는 팬 장치 이상 여부를 확인해야 함
- (냉각 장애) cooling fan failure detected 메시지가 발견되면 시스템 과열 위험이 있으므로 장비 상태 점검 및 팬 교체 검토 필요

# 임계치
fan_error_keywords

# 판단기준
- **양호**: `dmesg | grep -Ei 'fan|fan fail'` 결과에 관련 로그가 출력되지 않는 상태
- **경고**: `dmesg | grep -Ei 'fan|fan fail'` 결과에 팬 오류, 팬 속도 저하, 팬 장애 관련 로그가 하나 이상 출력되는 상태
- **참고**: 본 항목은 관련 로그 출력 여부를 기준으로 판단하며, 출력 결과가 존재하면 팬 장애 또는 냉각 이상 징후로 간주함
