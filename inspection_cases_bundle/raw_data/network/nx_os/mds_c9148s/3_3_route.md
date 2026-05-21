# 영역
서비스

# 세부 점검항목
라우팅 Table 상태

# 점검 내용
라우팅 Table 정상 여부 확인

# 구분
권고

# 명령어
```bash
show ip route
```

# 출력 결과(193.1.0.206)
```text
CITS-SAN1# show ip route

Codes: C - connected, S - static

Default gateway is 193.1.0.254

C 193.1.0.0/19 is directly connected, mgmt0

```

# 설명
- 명령어: IP 라우팅 테이블 상태를 확인하는 명령어
- Default Route가 목적지 경로를 찾지 못할 때 트래픽을 전송할 경로인 기본 gateway로 설정되어있어야함.

[참고]
1안. gateway값을 변수로 받아 일치하면 양호처리.
2안. 출력만 하고 담당자 확인처리.

# 임계치
gateway_ip

# 판단기준
- **양호**: `gateway_ip`와 'Default gateway is `gateway_ip`' 일치 상태
- **경고**: `gateway_ip`와 'Default gateway is `gateway_ip`' 불 일치 상태
- **확인 필요**: 명령어 실패 및 파싱 불가