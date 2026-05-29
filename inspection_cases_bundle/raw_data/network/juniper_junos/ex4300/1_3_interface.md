# 영역
자원 사용률

# 세부 점검항목
네트워크 인터페이스 사용률

# 점검 내용
인터페이스 사용현황을 확인하여 네트워크 병목여부 확인

# 구분
필수

# 명령어
```bash
show interfaces {{ interface_name }} statistics
```

# 출력 결과
```text
falcon@Center_Server_J4300_A> show interfaces ge-0/0/0 statistics
Physical interface: ge-0/0/0, Enabled, Physical link is Up
  Interface index: 646, SNMP ifIndex: 512
  Description: ## ATMS_▒▒▒▒DB-1_172.18.8.87_97 ##
  Link-level type: Ethernet, MTU: 1514, LAN-PHY mode, Speed: 1000mbps, Duplex: Full-Duplex, BPDU Error: None,
  Loop Detect PDU Error: None, Ethernet-Switching Error: None, MAC-REWRITE Error: None, Loopback: Disabled,
  Source filtering: Disabled, Flow control: Enabled, Auto-negotiation: Enabled, Remote fault: Online, Media type: Fiber
  Device flags   : Present Running
  Interface flags: SNMP-Traps Internal: 0x0
  Link flags     : None
  CoS queues     : 12 supported, 12 maximum usable queues
  Current address: f4:bf:a8:ed:ad:e3, Hardware address: f4:bf:a8:ed:ad:e3
  Last flapped   : 2026-05-18 16:43:53 KST (1w2d 21:07 ago)
  Statistics last cleared: Never
  Input rate     : 2136 bps (3 pps)
  Output rate    : 3592 bps (6 pps)
  Input errors: 0, Output errors: 0
  Active alarms  : None
  Active defects : None
  PCS statistics                      Seconds
    Bit errors                             0
    Errored blocks                         0
  Ethernet FEC statistics              Errors
    FEC Corrected Errors                    0
    FEC Uncorrected Errors                  0
    FEC Corrected Errors Rate               0
    FEC Uncorrected Errors Rate             0
  Interface transmit statistics: Disabled

  Logical interface ge-0/0/0.0 (Index 555) (SNMP ifIndex 513)
    Flags: Up SNMP-Traps 0x0 Encapsulation: Ethernet-Bridge
    Input packets : 1395327
    Output packets: 4395788
    Protocol eth-switch, MTU: 1514
      Flags: Is-Primary


```

# 설명
- 명령어: 특정 인터페이스 상태 및 통계 정보를 확인하는 명령어.
- 인터페이스 사용률은 Input rate, Output rate값을 인터페이스 Speed 값과 비교하여 계산한다.- 
- 수신 사용률(%): Input rate / speed * 100
- 송신 사용률(%): Output rate / speed * 100
- Speed: 1000mbps = 1000000000 bps
- ex) 출력기준
수신 사용률(%) = 2136 / 1000000000 * 100 = 약 0.0002136%
송신 사용률(%) = 3592 / 1000000000 * 100 = 약 0.0003592%


# 임계치
`interface_name`
- 점검 할 인터페이스 명
`max_interface_usage_percent`
- 최대 인터페이스 속도 값

# 판단기준
- **양호**: 수신 또는 송신 사용률이 `max_interface_usage_percent`이하인 상태
- **경고**: 수신 또는 송신 사용률이 `max_interface_usage_percent`초과인 상태
- **확인 필요**: 명령어 실패 및 파싱 불가