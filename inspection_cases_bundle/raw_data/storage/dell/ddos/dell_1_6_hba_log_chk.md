# 영역
로그

# 세부 점검항목
HBA 로그

# 점검 내용
HBA 작동이상 유무 점검 (Loop/port OFFLINE/ONLINE)

# 구분
필수

# 명령어
```bash
system show hardware
alerts show current
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

sysadmin@localhost# alerts show current
Id      Post Time                  Severity   Class               Object   Message
-----   ------------------------   --------   -----------------   ------   -------------------------------------------------------
p0-96   Mon Mar 30 14:33:16 2026   ERROR      SystemMaintenance            EVT-SMTOOL-00001: Error communicating with mail server.
-----   ------------------------   --------   -----------------   ------   -------------------------------------------------------
There is 1 active alert.

```

# 설명
- system show hardware 명령어를 통해 장비에 장착된 HBA(Fibre Channel 카드) 및 Port 구성을 확인
- Fibre Channel 카드가 정상적으로 인식되는지 포트가 정상 표시 되는지 점검 필요
- alerts show current 명령어를 통해 현재 활성화된 장애(Alert) 로그를 확인할 수 있으며, HBA Port Offline, Link Down, Loop 장애 등의 FC 관련 오류 여부를 점검 가능
※ FC(HBA) 장애 발생 시 백업/스토리지 연결 장애 및 SAN 통신 문제 발생 가능

# 임계치
hba_device_keywords = [
    "fibrechannel",
    "fc",
    "hba",
    "scsi target"
]
hba_status_keywords = [
    "offline",
    "loop",
    "link down"
]


# 판단기준
- **양호**: system show hardware 출력에 Fibre Channel 카드 및 Port 정보가 정상 표시되며, alerts show current 출력에서 `hba_device_keywords`와 `hba_status_keywords` 조건을 동시에 만족하는 장애 메시지가 존재하지 않을 경우
- **경고**: system show hardware 출력에 Fibre Channel 카드 및 Port 정보가 정상 표시되지 않거나, alerts show current 출력에서 `hba_device_keywords`와 `hba_status_keywords` 조건을 동시에 만족하는 장애 메시지가 존재할 경우
- **확인 필요**: 명령어 수행 실패 또는 출력 결과를 확인할 수 없는 경우
