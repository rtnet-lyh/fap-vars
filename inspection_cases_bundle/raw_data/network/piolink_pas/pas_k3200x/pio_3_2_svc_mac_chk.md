# 영역
서비스  

# 세부 점검항목
Mac/Arp Table 상태 확인

# 점검 내용
Mac/Arp Table 정상 여부 확인

# 구분
권고

# 명령어 (2개 명령어 필요)
```bash
show mac
show arp
```

# 출력 결과 (테스트 서버: 172.31.247.114)
```text
Center_PAS-K3200X_A# show mac

================================================================================
  MAC
 ------------------------------------------------------------------------------
    Ageing Time          : 300

    Mac Table
       Port  Vid   Mac Address       Status  Type
       12    808   40:5b:7f:6d:53:60 forward dynamic
       13    808   00:06:c4:90:0d:77 forward dynamic
                   00:62:0b:9e:e9:86 forward dynamic
                   0e:00:e8:15:06:38 forward dynamic
                   14:02:ec:74:e2:10 forward dynamic
                   40:a6:b7:29:25:dc forward dynamic
                   44:8a:5b:dc:44:02 forward dynamic
                   48:df:37:59:78:40 forward dynamic
                   48:df:37:59:78:d0 forward dynamic
                   54:80:28:40:1b:14 forward dynamic
                   54:80:28:40:1b:38 forward dynamic
                   68:05:ca:e0:be:bc forward dynamic
                   68:05:ca:e4:28:1c forward dynamic
                   68:05:ca:e4:2b:38 forward dynamic
                   68:05:ca:e4:2b:d4 forward dynamic
                   68:05:ca:e4:2b:f8 forward dynamic
                   68:05:ca:e4:2c:08 forward dynamic
                   68:05:ca:e4:2c:8c forward dynamic
                   68:05:ca:e4:2c:d4 forward dynamic
                   68:05:ca:fd:28:fc forward dynamic
                   68:05:ca:fd:2c:2c forward dynamic
                   80:18:44:e9:4d:88 forward dynamic
                   88:90:09:93:70:80 forward dynamic
                   a0:36:9f:df:6d:08 forward dynamic
                   a4:bf:01:0f:e5:b1 forward dynamic
                   a4:bf:01:75:0a:7c forward dynamic
                   b4:96:91:97:35:cf forward dynamic
                   b4:96:91:97:37:35 forward dynamic
                   c8:fe:6a:91:c0:21 forward dynamic
                   d0:94:66:15:5b:38 forward dynamic
                   d0:94:66:15:5b:3a forward dynamic
                   d4:f5:ef:0d:f6:54 forward dynamic
                   d8:d3:85:f7:ec:0e forward dynamic
                   d8:d3:85:f8:4a:b0 forward dynamic
                   d8:d3:85:f8:4b:68 forward dynamic
                   d8:d3:85:f8:e4:11 forward dynamic
                   ec:e7:a7:06:0d:d8 forward dynamic
                   f4:bf:a8:ed:ad:e1 forward dynamic
                   f4:bf:a8:ed:ad:ff forward dynamic
                   f4:bf:a8:ed:ae:40 forward dynamic
       16    422   00:10:f3:a4:1e:d9 forward dynamic
       18    808   04:32:01:5a:2a:c0 forward dynamic
       agg1  422   00:06:c4:90:0d:77 forward dynamic
                   00:10:f3:a4:22:f1 forward dynamic
================================================================================

Center_PAS-K3200X_A# show arp

================================================================================
  ARP
 ------------------------------------------------------------------------------
    Timeout (sec)               : 30
    Locktime (1/100 sec)        : 100
    Proxy Arp Status            : disable
    Proxy Arp Delay (1/100 sec) : 0
    Proxy Arp Running           : disable

    Static                      :

    Dynamic
       IP Address     MAC Address       Interface State
       172.18.8.1     04:32:01:5a:2a:c0 V808      REACHABLE
       172.18.8.4     00:62:0b:9e:e9:86 V808      STALE
       172.18.8.11    54:80:28:40:1b:38 V808      REACHABLE
       172.18.8.14    d8:d3:85:f8:4a:b0 V808      REACHABLE
       172.18.8.15    14:02:ec:74:e2:10 V808      DELAY
       172.18.8.17    48:df:37:59:78:40 V808      REACHABLE
       172.18.8.19    68:05:ca:e4:2c:8c V808      REACHABLE
       172.18.8.20    68:05:ca:e4:28:1c V808      REACHABLE
       172.18.8.22    68:05:ca:e4:2b:d4 V808      REACHABLE
       172.18.8.23    d8:d3:85:f8:4b:68 V808      REACHABLE
       172.18.8.24    54:80:28:40:1b:14 V808      REACHABLE
       172.18.8.25    80:18:44:e9:4d:88 V808      REACHABLE
       172.18.8.26    d0:94:66:15:5b:38 V808      REACHABLE
       172.18.8.27    a4:bf:01:0f:e5:b1 V808      REACHABLE
       172.18.8.28    a4:bf:01:75:0a:7c V808      REACHABLE
       172.18.8.29    68:05:ca:e0:be:bc V808      REACHABLE
       172.18.8.30    ec:e7:a7:06:0d:d8 V808      REACHABLE
       172.18.8.31    d8:d3:85:f8:e4:11 V808      REACHABLE
       172.18.8.34    d4:f5:ef:0d:f6:54 V808      STALE
       172.18.8.41    a0:36:9f:df:6d:08 V808      REACHABLE
       172.18.8.45    d8:d3:85:f7:ec:0e V808      REACHABLE
       172.18.8.52    68:05:ca:e4:2b:38 V808      REACHABLE
       172.18.8.53    68:05:ca:e4:2b:f8 V808      REACHABLE
       172.18.8.54    68:05:ca:e4:2c:08 V808      DELAY
       172.18.8.71    40:a6:b7:29:25:dc V808      REACHABLE
       172.18.8.81    b4:96:91:97:35:cf V808      REACHABLE
       172.18.8.82    b4:96:91:97:37:35 V808      REACHABLE
       172.18.8.87    68:05:ca:fd:2c:2c V808      REACHABLE
       172.18.8.88    68:05:ca:fd:28:fc V808      DELAY
       172.18.8.91    b4:96:91:97:35:cf V808      REACHABLE
       172.18.8.92    b4:96:91:97:37:35 V808      REACHABLE
       172.18.8.93    68:05:ca:e4:2c:d4 V808      DELAY
       172.18.8.97    68:05:ca:fd:2c:2c V808      REACHABLE
       172.18.8.98    68:05:ca:fd:28:fc V808      REACHABLE
       172.18.8.191   40:5b:7f:6d:53:60 V808      REACHABLE
       172.18.8.211   f4:bf:a8:ed:ad:e1 V808      REACHABLE
       172.18.8.212   c8:fe:6a:91:c0:21 V808      REACHABLE
       172.18.8.230   44:8a:5b:dc:44:02 V808      STALE
       172.18.8.253   00:06:c4:90:0d:77 V808      STALE
       172.31.247.123 00:10:f3:a4:1e:d9 V422      STALE
       172.31.247.126 00:10:f3:a4:1e:d9 V422      DELAY
================================================================================
```

# 설명
※ show mac 명령을 통해 MAC Address Table 상태 확인
- MAC Address와 연결된 Port/VLAN 학습 상태를 확인 가능
- Status 값이 forward인 경우 정상 forwarding 상태를 의미
- Type 값이 dynamic 인 경우 통신을 통해 자동 학습된 MAC Address를 의미
- show arp 명령을 통해 IP Address와 MAC Address 매핑 상태를 확인
- State 값은 ARP Neighbor 상태를 의미
- REACHABLE, STALE, DELAY 상태는 정상 범위로 판단함

# 임계치
expected_mac_status = "forward"
valid_arp_state = [
  "REACHABLE",
  "STALE",
  "DELAY"
]

# 판단기준
- **양호**: MAC Address가 정상 학습 되어 있으며(Port값 존재) MAC Status 값이 `expected_mac_status`이고 ARP State 값이 `valid_arp_state`에 포함된 상태
- **경고**: MAC Address가 미학습 또는 MAC Status 값이 `expected_mac_status`가 아니거나 ARP State가 `valid_arp_state`에 포함되지 않은 상태
- **확인 필요**: 명령어 수행 실패 또는 출력 결과를 확인할 수 없는 경우
