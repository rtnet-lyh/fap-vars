# 영역
로그

# 세부 점검항목
CONTROLLER 로그

# 점검 내용
컨트롤러 오류 및 이상 유무 점검 (Controller fail)

# 구분
필수

# 명령어
```bash
alerts show current
```

# 출력 결과 (테스트 서버: 172.31.247.114)
```text
sysadmin@localhost# alerts show current
Id      Post Time                  Severity   Class               Object   Message
-----   ------------------------   --------   -----------------   ------   -------------------------------------------------------
p0-96   Mon Mar 30 14:33:16 2026   ERROR      SystemMaintenance            EVT-SMTOOL-00001: Error communicating with mail server.
-----   ------------------------   --------   -----------------   ------   -------------------------------------------------------
There is 1 active alert.

```

# 설명
- alerts show current 명령어를 통해 시스템 전체 이벤ㄴ트 및 컨트롤러 관련 로그 확인
- Storage Controller, NVRAM, HW, Disk, FC, System Error 등을 확인 가능

# 임계치
controller_device_keywords = [
    "controller",
    "disk controller"
]
controller_status_keywords = [
    "failed",
    "failure",
    "low",
    "disabled",
    "reset",
    "error"
]


# 판단기준
- **양호**: alerts show current 출력에서 `controller_device_keywords`와 `controller_status_keywords` 조건을 동시에 만족하는 장애 메시지가 존재하지 않을 경우
- **경고**: alerts show current 출력에서 `controller_device_keywords`와 `controller_status_keywords` 조건을 동시에 만족하는 장애 메시지가 존재할 경우
- **확인 필요**: 명령어 수행 실패 또는 출력 결과를 확인할 수 없는 경우
