# 영역
로그

# 세부 점검항목
전원공급 장치 점검

# 점검 내용
스토리지 SPS Fault 여부

# 구분
필수

# 명령어
```bash
system show hardware
```

# 출력 결과 (테스트 서버: 172.31.247.114)
```text
sysadmin@localhost# system show hardware
Slot   Vendor     Device                            Ports
----   --------   -------------------------------   --------------
M      Broadcom   BCM5727 1GbE                      Ma
0      EMC        NVRAM 8GB Model 3
1      Broadcom   Quad Port 10GBase-T               1a, 1b, 1c, 1d
2      (empty)    (empty)
3      (empty)    (empty)
4      (empty)    (empty)
5      EMC        Dual Port 16 Gbps Fibre Channel   5a, 5b
6      EMC        Dual Port 16 Gbps Fibre Channel   6a, 6b
7      EMC        PMC Quad Port 6 Gbps SAS          7a, 7b, 7c, 7d
----   --------   -------------------------------   --------------

```

# 설명
- system show hardware 명령어를 통해 스토리지 컨트롤러(Fibre Channel, SAS, NVRAM) 장착 및 인식 상태를 확인할 수 있음
- 컨트롤러 장치(Device) 및 Port 정보가 정상 표시되는지 점검 필요

# 임계치
power_device_keywords = [
    "power",
    "psu",
    "sps",
    "voltage",
    "power supply"
]

power_status_keywords = [
    "failed",
    "fault",
    "offline",
    "error",
    "critical"
]

# 판단기준
- **양호**: 출력 결과의 Message에 `power_device_keywords`와 `power_status_keywords` 조건을 동시에 만족하는 관련 장애 메시지가 없는 경우
- **경고**: 출력 결과의 Message에 `power_device_keywords`와 `power_status_keywords` 조건을 동시에 만족하는 관련 장애 메시지가 있는 경우
- **확인 필요**: 명령어 수행 실패 또는 출력 결과를 확인할 수 없는 경우
