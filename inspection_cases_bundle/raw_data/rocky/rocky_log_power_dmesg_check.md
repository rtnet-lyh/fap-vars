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
dmesg | grep -Ei 'power|psu|PS Failed'
```

# 출력 결과
```text
[   18.123456] ipmi_si dmi-ipmi-si.0: Power supply PSU1 failure detected
[   18.124102] ipmi_si dmi-ipmi-si.0: PSU2 status changed: predictive failure
[   18.124889] platform power_mon: PS Failed alarm asserted
[   18.125401] hwmon hwmon3: power unit input lost
[   18.126033] systemd[1]: Warning: redundant power supply degraded
```

# 설명
- (전원 오류 메시지) power, PSU, PS Failed 관련 메시지가 발견되면 전원 공급 장치 이상 또는 이중화 전원 상태 저하 가능성이 있으므로 하드웨어 점검 필요
- (PSU 장애 메시지) PSU failure detected 또는 predictive failure 메시지가 확인되면 전원 공급 장치 고장 또는 고장 예측 상태를 의미하므로 PSU 상태 점검 및 교체 검토 필요
- (전원 입력 상실) power unit input lost 메시지가 발견되면 전원 입력 문제, 케이블 불량, 전원 모듈 이상 여부를 확인해야 함
- (이중화 전원 저하) redundant power supply degraded 메시지가 확인되면 이중화 전원 구성 중 일부가 비정상 상태일 수 있으므로 즉시 점검 권고

# 임계치
power_error_keywords

# 판단기준
- **양호**: `dmesg | grep -Ei 'power|psu|PS Failed'` 결과에 관련 로그가 출력되지 않는 상태
- **경고**: `dmesg | grep -Ei 'power|psu|PS Failed'` 결과에 전원 공급 장치 오류, PSU 장애, 전원 입력 상실, PS Failed 관련 로그가 하나 이상 출력되는 상태
- **참고**: 본 항목은 관련 로그 출력 여부를 기준으로 판단하며, 출력 결과가 존재하면 전원 장치 또는 전원 이중화 이상 징후로 간주함