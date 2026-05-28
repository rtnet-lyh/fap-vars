# 영역
기타

# 세부 점검항목
전원, FAN 등 점검

# 점검 내용
장비의 물리적인 하드웨어(전원, Fan, 라우팅엔진, 라인카드 등) 상태 점검

# 구분
권고

# 명령어
```bash
show hardwarestatus
```

# 출력 결과 (테스트 서버: 172.31.247.114)
```text
Center_PAS-K3200X_A# show hardwarestatus

================================================================================
  HARDWARESTATUS
 ------------------------------------------------------------------------------
    Temperature
       Name   Degree
       Switch +31.5 C
       Core 0 +48.0 C  (high = +82.0 C, crit = +104.0 C)
       Core 1 +48.0 C  (high = +82.0 C, crit = +104.0 C)
       Core 2 +47.0 C  (high = +82.0 C, crit = +104.0 C)
       Core 3 +47.0 C  (high = +82.0 C, crit = +104.0 C)

    LED
        Stat             : OFF

    Voltage
        Power1           : ON
        Power2           : ON

    Fan
       Name   Status
       CPU    ON
       Rear 1 ON
       Rear 2 ON
       Rear 3 ON
       Switch ON
       Module ON

    Accelerator
        SSL/TLS          : OFF
        Health           : None

    Storage
        Condition        : Good
================================================================================

```

# 설명
- 전원(Power), Fan, Storage 상태 등을 점검
- 장비 내부 센서 기반 HW 상태 확인 가능
- 전원 장애, Fan 이상, 전원장치 이상 여부를 점검


# 임계치


# 판단기준
- **양호**: 모든 Power(Voltage) 상태가 'ON'이며, Fan 상태가 'On'이고, Storage 상태가 'Good'인 경우
- **경고**: Power(Voltage) 상태가 'OFF'이거나 Fan 상태가 'OFF'/'FAIL'이거나 Storage 상태가 'Good'이 아닌 경우
- **확인 필요**: 명령어 수행 실패 또는 출력 결과를 확인할 수 없는 경우
