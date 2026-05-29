# 영역
자원 사용률

# 세부 점검항목
CPU 사용률

# 점검 내용
CPU 자원 사용률 확인

# 구분
필수

# 명령어
```bash
show chassis routing-engine
```

# 출력 결과
```text
falcon@Center_Server_J4300_A> show chassis routing-engine
Routing Engine status:
  Slot 0:
    Current state                  Master
    Temperature                 48 degrees C / 118 degrees F
    CPU temperature             48 degrees C / 118 degrees F
    DRAM                      3072 MB
    Memory utilization          48 percent
    5 sec CPU utilization:
      User                       6 percent
      Background                 0 percent
      Kernel                     3 percent
      Interrupt                  0 percent
      Idle                      91 percent
    Model                          EX4300-32F
    Serial ID                      TW3720310093
    Start time                     2020-11-12 07:19:14 KST
    Uptime                         2023 days, 13 hours, 54 minutes, 30 seconds
    Last reboot reason             0x1:power cycle/failure
    Load averages:                 1 minute   5 minute  15 minute
                                       0.15       0.16       0.10

```

# 설명
- 명령어: 라우팅 엔진 상태를 확인하는 명령어.
- 5 sec CPU utilization의 Idle 값은 사용되지 않고 남아있는 CPU의 비율을 의미함.
- CPU사용률: 100 - Idle

# 임계치
max_cpu_usage_percent

# 판단기준
- **양호**: CPU 사용률이 `max_cpu_usage_percent` 이하인 상태
- **경고**: CPU 사용률이 `max_cpu_usage_percent` 초과인 상태
- **확인 필요**: 명령어 실패 및 파싱 불가.