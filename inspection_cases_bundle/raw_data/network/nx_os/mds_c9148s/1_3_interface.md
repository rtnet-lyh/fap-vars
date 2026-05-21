# 영역
자원 사용률

# 세부 점검항목
네트워크 인터페이스 사용률

# 점검 내용
인터페이스 송신/수신 부하 상태를 확인하여 대역폭 사용률 점검(80% 미만 권고).

# 구분
필수

# 명령어
```bash
show interface
```

# 출력 결과
```text
fc1/10 is up
    Hardware is Fibre Channel, SFP is short wave laser w/o OFC (SN)
    Port WWN is 20:0a:00:3a:9c:16:48:10
    Admin port mode is auto, trunk mode is on
    snmp link state traps are enabled
    Port mode is F, FCID is 0xa90e00
    Port vsan is 10
    Speed is 8 Gbps
    Rate mode is dedicated
    Transmit B2B Credit is 12
    Receive B2B Credit is 64
    Receive data field Size is 2112
    Beacon is turned off
    admin fec state is down
    oper fec state is down
    5 minutes input rate 18940800 bits/sec,2367600 bytes/sec, 2254 frames/sec
    5 minutes output rate 64165888 bits/sec,8020736 bytes/sec, 4478 frames/sec
      6141735865596 frames input,10778094664129100 bytes
        0 discards,0 errors
        0 invalid CRC/FCS,0 unknown class
        0 too long,0 too short
      1996989242795 frames output,2432660549947668 bytes
        0 discards,0 errors
      0 input OLS,0  LRR,1 NOS,0 loop inits
      2 output OLS,2 LRR, 1 NOS, 2 loop inits
      64 receive B2B credit remaining
      12 transmit B2B credit remaining
      12 low priority transmit B2B credit remaining
    Interface last changed at Sat Jan 15 01:00:44 2022

    Last clearing of "show interface" counters  :never

fc1/11 is down (Link failure or not-connected)
    Hardware is Fibre Channel, SFP is short wave laser w/o OFC (SN)
    Port WWN is 20:0b:00:3a:9c:16:48:10
    Admin port mode is auto, trunk mode is on
    snmp link state traps are enabled
    Port vsan is 10
    Receive data field Size is 2112
    Beacon is turned off
    5 minutes input rate 0 bits/sec,0 bytes/sec, 0 frames/sec
    5 minutes output rate 0 bits/sec,0 bytes/sec, 0 frames/sec
      1 frames input,176 bytes
        0 discards,0 errors
        0 invalid CRC/FCS,0 unknown class
        0 too long,0 too short
      27402085 frames output,1096083536 bytes
        0 discards,0 errors
      0 input OLS,0  LRR,0 NOS,15071036 loop inits
      1370105 output OLS,0 LRR, 685057 NOS, 685059 loop inits
    Last clearing of "show interface" counters  :never

```

# 설명
- 명령어: 인터페이스 상태, 속도, 송수신 트래픽, 오류 등을 확인하는 명령어.
- 상태가 UP인 인터페이스만 점검 ex)fc1/10 is up
- 5 minutes input rate: 최근 5분 평균 수신 트래픽 사용량, 5 minutes output rate: 최근 5분 평균 송신 트래픽 사용량
- 수신 사용률(%): 5 minutes input rate / speed * 100
- 송신 사용률(%): 5 minutes output rate / speed * 100
- ex) 출력기준
수신 사용률(%) = 18940800 / 8000000000 * 100 = 약 0.24%
송신 사용률(%) = 64165888 / 8000000000 * 100 = 약 0.80%

[참고]
- 범정부 문서 기준 'txload','rxload'를 점검해야하지만, SAN장비에서는 결과 값이 달라서 rate 값으로 점검.

# 임계치
max_interface_usage_percent

# 판단기준
- **양호**: 상태가 UP인 인터페이스의 수신 또는 송신 사용률이 `max_interface_usage_percent`이하인 상태
- **경고**: 상태가 UP인 인터페이스의 수신 또는 송신 사용률이 `max_interface_usage_percent`초과인 상태
- **확인 필요**: 명령어 실패 및 '5 minutes input rate' 파싱 불가