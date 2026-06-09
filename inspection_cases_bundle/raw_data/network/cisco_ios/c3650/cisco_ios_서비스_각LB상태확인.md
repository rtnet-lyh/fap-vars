# 영역
NETWORK

# 세부 점검항목
각 LB 상태 확인

# 점검 내용
부하 분산 상태 점검 및 real 서버 Health-Check 상태 점검

# 구분
권고

# 명령어
```text
show ip slb vserver
show ip slb real
```

# 출력 결과
```text
Virtual Server VS_WEB, IP address 203.0.113.10
  State           : OPERATIONAL
  Protocol        : tcp
  Virtual port    : 80
  Serverfarm      : FARM_WEB

Real Server 10.10.10.11
  State           : OPERATIONAL
  Connections     : 120
  Failures        : 0

Real Server 10.10.10.12
  State           : OPERATIONAL
  Connections     : 118
  Failures        : 0
```

# 설명
- Cisco IOS 장비에서 SLB 기능을 사용하는 경우 `show ip slb vserver`, `show ip slb real` 명령으로 가상 서비스와 real 서버 상태를 확인할 수 있다.
- Virtual Server 상태가 `OPERATIONAL` 이어야 하고, 연결된 real 서버가 정상 `OPERATIONAL` 상태인지 확인해야 한다.
- real 서버의 `Failures` 증가, `OUT OF SERVICE`, `FAILED` 상태는 헬스체크 실패나 백엔드 장애 가능성을 의미한다.
- 장비에서 SLB 기능을 사용하지 않는 환경이라면 해당 명령이 지원되지 않을 수 있으므로 적용 여부를 먼저 확인한다.

# 임계치
max_down_real_server_count
max_out_of_service_vserver_count

# 판단기준
- **양호**: Virtual Server가 정상 상태이고 비정상 real 서버 수가 각 임계치 이하인 경우
- **주의**: 일부 real 서버의 헬스체크 실패가 있으나 서비스 전체는 유지되고 있는 경우
- **경고**: Virtual Server가 비정상 상태이거나 real 서버 Down 수가 임계치를 초과하는 경우
- **확인 필요**: 대상 장비에서 SLB 기능을 사용하지 않거나 명령이 지원되지 않아 적용 대상 여부 확인이 필요한 경우

