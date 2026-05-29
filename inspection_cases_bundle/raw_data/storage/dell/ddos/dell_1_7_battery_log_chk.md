# 영역
로그

# 세부 점검항목
CACHE BATTERY 로그

# 점검 내용
캐쉬 배터리 오류 및 이상 유무 점검 (Battery fail)

# 구분
필수

# 명령어
```bash
enclosure show nvram
```

# 출력 결과 (테스트 서버: 172.31.247.114)
```text
sysadmin@localhost# enclosure show nvram
Enclosure 1
        NVRAM Cards:
                Card   Component                 Value
                ----   -----------------------   ----------------------------------------------------------------------
                1      Slot                      0
                       Firmware version          0.0.81
                       Memory size               7.93 GiB
                       Errors                    0 memory (0 uncorrectable), 0 PCI, 0 controller
                       Flash controller Errors   0 Cfg Err, 0 PANIC, 0 Bus Hang, 0 Bad Blk Warn, 0 Bkup Err, 0 Rstr Err
                       Board temperature         38 C
                       CPU temperature           50 C
                       Number of batteries       1
                ----   -----------------------   ----------------------------------------------------------------------
        NVRAM Batteries:
                Card   Battery   Status   Charge   Charging   Time To       Temperature   Voltage
                                                   Status     Full Charge
                ----   -------   ------   ------   --------   -----------   -----------   -------
                1      1         ok       97 %     enabled    0 mins        34 C          4.051 V
                ----   -------   ------   ------   --------   -----------   -----------   -------

```

# 설명
- enclosure show nvram 명령어를 통해 Cache Battery(Battery Backup Unit) 오류 및 이상 여부를 확인
- Data Domain OS에서는 일반 스토리지의 Cache Battery 역할을 NVRAM Battery가 수행하며, 전원 장애 발생 시 캐시 데이터 보호 기능을 담당함

# 임계치

# 판단기준
- **양호**: 명령어 출력값에서 NVRAM Batteries의 Status 값이 'ok'인 경우
- **경고**: 명령어 출력값에서 NVRAM Batteries의 Status 값이 'ok'가 아닌 경우
- **확인 필요**: 명령어 수행 실패 또는 출력 결과를 확인할 수 없는 경우
