# 영역
기타

# 세부 점검항목
전원, FAN 등 점검

# 점검 내용
장비의 물리적인 하드웨어(전원, FAN, 라우팅엔진, 라인카드 등) 상태 점검

# 구분
권고

# 명령어
```bash
show environment
```

# 출력 결과
```text
CITS-SAN1# show environment
Power Supply:
Voltage: 12 Volts
-----------------------------------------------------
PS  Model                Power       Power     Status
                         (Watts)     (Amp)
-----------------------------------------------------
1   DS-C48S-300AC         300.00     25.00     Ok
2   DS-C48S-300AC         300.00     25.00     Ok


Mod Model                Power     Power       Power     Power       Status
                         Requested Requested   Allocated Allocated
                         (Watts)   (Amp)       (Watts)   (Amp)
--- -------------------  -------   ----------  --------- ----------  ----------
1    DS-C9148S-K9-SUP     150.00    12.50      150.00    12.50       Powered-Up


Power Usage Summary:
--------------------
Power Supply redundancy mode:                 Redundant
Power Supply redundancy operational mode:     Redundant

Total Power Capacity                              300.00 W

Total Power Allocated (budget)                    150.00 W
                                                -------------
Total Power Available                             150.00 W
                                                -------------
Clock:
----------------------------------------------------------
Clock           Model                Hw         Status
----------------------------------------------------------
A               Clock Module         --         NotSupported/None


Fan:
------------------------------------------------------
Fan             Model                Hw         Status
------------------------------------------------------
ChassisFan1     FAN Module 1         --         Ok
ChassisFan2     FAN Module 2         --         Ok
ChassisFan3     FAN Module 3         --         Ok
ChassisFan4     FAN Module 4         --         Ok
Fan_in_PS1      --                   --         Ok
Fan_in_PS2      --                   --         Ok
Fan Air Filter : NotSupported


Temperature:
--------------------------------------------------------------------
Module   Sensor        MajorThresh   MinorThres   CurTemp     Status
                       (Celsius)     (Celsius)    (Celsius)
--------------------------------------------------------------------
1        Outlet1  (s1)   75              60          34         Ok
1        Outlet2  (s2)   75              60          32         Ok
1        Intake1  (s3)   75              60          32         Ok
1        Intake2  (s4)   75              60          32         Ok
1        FC-SOC1  (s5)   115             105         40         Ok


```


# 설명
- 명령어: 장비의 물리적인 하드웨어 상태를 확인하는 명령어.
- 각 status 값의 비정상 키워드를 변수로 설정 or 하드코딩

[참고]
- Power Supply: 장착된 전원 공급 장치
- Power Usage Summary: 전원과 전력상태 요약
- Clock:하드웨어 클럭 모듈 상태
- Fan: 내부 냉각 FAN 동작 상태
- Temperature: 내부 온도 센서 상태
- 비정상키워드 목록: fail|faulty|warning|critical|major|minor|down|unknown

# 임계치

# 판단기준
- **양호**: 비정상 키워드 미 탐지
- **경고**: 비정상 키워드 탐지
- **확인 필요**: 명령어 실패 및 파싱 실패