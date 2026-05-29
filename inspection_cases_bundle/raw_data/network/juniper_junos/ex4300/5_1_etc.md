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
falcon@Center_Server_J4300_B> show chassis environment
Class Item                           Status     Measurement
Power FPC 0 Power Supply 0           OK
      FPC 0 Power Supply 1           OK
Temp  FPC 0 CPU                      OK         50 degrees C / 122 degrees F
      FPC 0 NW-PFE                   OK         40 degrees C / 104 degrees F
      FPC 0 SE-PFE                   OK         35 degrees C / 95 degrees F
      FPC 0 PHY-4/5                  OK         34 degrees C / 93 degrees F
      FPC 0 MGMT PHY                 OK         29 degrees C / 84 degrees F
Fans  FPC 0 Fan 0                    OK         Spinning at normal speed
      FPC 0 Fan 0 Airflow            OK         Airflow Out (AFO)
      FPC 0 Fan 1                    OK         Spinning at normal speed
      FPC 0 Fan 1 Airflow            OK         Airflow Out (AFO)


```


# 설명
- 명령어: 장비의 물리적인 하드웨어 환경 상태를 확인하는 명령어.


# 임계치

# 판단기준
- **양호**: Status 값이 모두 'OK'인 경우
- **경고**: Status 값이 하나라도 'OK'가 아닌 경우
- **확인 필요**: 명령어 실패 및 파싱 실패