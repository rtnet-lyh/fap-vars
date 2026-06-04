# 영역
서비스  

# 세부 점검항목
이중화 구성 상태 점검

# 점검 내용
Failover 상태 확인

# 구분
권고

# 명령어
```bash
show failover
```

# 출력 결과 (테스트 서버: 172.31.247.114)
```text
Center_PAS-K3200X_A# show failover

================================================================================
  FAILOVER
 ------------------------------------------------------------------------------
    A-A Failover Method  : disable
    Redirect Vlan        :
    Delay-Time           : 10

    Session-Sync
        Status                     : disable
        Live update interval (10 msec) : 100
        Full update interval (sec) : 30
        Update method              : live
        Peer                       : node2

        Interface
            Name                   :
            IPv4 Address           :
            Peer IP Address        :
            Hc-Retry               : 3
            Health                 : inact

    Vrrp
       VRID  Mode           Running Status Total Priority VLAN  VIP            VMAC
       254   active-standby master  enable 111   105      V422  172.31.247.113 00:00:5e:00:01:fe
                                                          V808  172.18.8.254   00:00:5e:00:01:fe

    Vrrp6                :

    Ha
        Running                   : stop
        Status                    : disable

        Interface                 :

        Node                      :

        Default State             : master
        Heartbeat Interval (100 msec) : 10
        Retry                     : 3
        VMAC                      : enable
================================================================================

```

# 설명
- show failover 명령을 통해 이중화(Failover) 및 VRRP 상태를 확인
- Mode: Active/Standby 구성 여부를 확인
- Running: 현재 장비 역할(Master/backup)을 확인
- Status: Vrrp 활성 상태(enable/disable)를 확인 
- VIP(Virtual IP): 이중화 장비 간 공유되는 가상 IP 의미
- 장애 발생 시 다른 장비로 서비스가 자동 절체(Failover) 되는지 확인 가능 

# 임계치

# 판단기준
- **양호**: Status 값이 'enable'이며 Runinng 값이 master 또는 backup 상태 
- **경고**: Status 값이 'disable'이며 Runinn g값이 비정상인 상태
- **확인 필요**: 명령어 수행 실패 또는 출력 결과를 확인할 수 없는 경우
※참고: 이중화 구성 정상 여부는 양쪽 장비의 Running(Master/backup) 상태를 함께 확인해야 함
