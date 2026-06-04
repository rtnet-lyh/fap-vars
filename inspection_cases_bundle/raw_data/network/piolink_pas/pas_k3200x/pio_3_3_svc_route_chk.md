# 영역
서비스  

# 세부 점검항목
라우팅 Table 상태

# 점검 내용
Static/OSPF/BGP 라우팅 Table 정상 여부 확인

# 구분
권고

# 명령어
```bash
show route
```

# 출력 결과 (테스트 서버: 172.31.247.114)
```text
Center_PAS-K3200X_A# show route

================================================================================
  ROUTE
 ------------------------------------------------------------------------------
    Default-Gateway      : 172.31.247.126

    Network
       Destination       Gateway Interface
       172.31.247.112/28 0.0.0.0 V422
       172.18.8.0/24     0.0.0.0 V808
       192.168.100.0/24  0.0.0.0 mgmt
================================================================================

```

# 설명
- Default-Gateway: 기본 게이트웨이
- Destination: 목적지 네트워크
- Gateway: Next-hpt
- Interface: 연결 인터페이스

# 임계치

# 판단기준
- **양호**: Default-Gateway 및 Route 정보(Destination/Interface)가 정상 존재하는 상태
- **경고**: Default-Gateway 또는 Route 정보(Destination/Interface)가 존재하지 않는 상태
- **확인 필요**: 명령어 수행 실패 또는 출력 결과를 확인할 수 없는 경우
