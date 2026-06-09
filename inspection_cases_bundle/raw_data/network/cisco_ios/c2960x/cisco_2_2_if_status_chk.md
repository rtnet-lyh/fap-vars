# 영역
네트워크

# 세부 점검항목
인터페이스/모듈 상태

# 점검 내용
Cisco 장비의 인터페이스/모듈 상태 점검

# 구분
필수

# 명령어
```bash
show interface status
```

# 출력 결과
```text
[OS: Cisco IOS] 추출된 결과입니다.
C2960X_Service#show interface status

Port      Name               Status       Vlan       Duplex  Speed Type
Gi0/1     ===Service_FW_eth1 connected    99         a-full a-1000 10/100/1000BaseTX
Gi0/2     ===10F===          connected    99         a-full a-1000 10/100/1000BaseTX
Gi0/3     ===B1F===          notconnect   99           auto   auto 10/100/1000BaseTX
Gi0/4                        disabled     1            auto   auto 10/100/1000BaseTX
Gi0/5     ===fileserver_NAS= connected    99         a-full a-1000 10/100/1000BaseTX
Gi0/6                        disabled     99           auto   auto 10/100/1000BaseTX
Gi0/7                        disabled     99           auto   auto 10/100/1000BaseTX
Gi0/8                        disabled     99           auto   auto 10/100/1000BaseTX
Gi0/9                        disabled     99           auto   auto 10/100/1000BaseTX
Gi0/10                       disabled     99           auto   auto 10/100/1000BaseTX
Gi0/11                       disabled     99           auto   auto 10/100/1000BaseTX
Gi0/12                       disabled     99           auto   auto 10/100/1000BaseTX
Gi0/13                       disabled     99           auto   auto 10/100/1000BaseTX
Gi0/14                       disabled     99           auto   auto 10/100/1000BaseTX
Gi0/15                       disabled     99           auto   auto 10/100/1000BaseTX
Gi0/16                       disabled     99           auto   auto 10/100/1000BaseTX
Gi0/17                       disabled     99           auto   auto 10/100/1000BaseTX
Gi0/18                       disabled     99           auto   auto 10/100/1000BaseTX
Gi0/19                       disabled     99           auto   auto 10/100/1000BaseTX
Gi0/20                       disabled     99           auto   auto 10/100/1000BaseTX
Gi0/21                       notconnect   99           auto   auto 10/100/1000BaseTX
Gi0/22                       notconnect   99           auto   auto 10/100/1000BaseTX
Gi0/23                       notconnect   99           auto   auto 10/100/1000BaseTX
Gi0/24                       disabled     99           auto   auto 10/100/1000BaseTX
Gi0/25                       disabled     99           auto   auto Not Present
Gi0/26                       disabled     99           auto   auto Not Present
Fa0       ===MGMT_Fa0/4===   connected    routed     a-full  a-100 10/100BaseTX



---
```

# 설명
- `show interface status` 명령을 통해 주요 서비스 포트들의 Link Up/Down 상태 및 속도/Duplex 설정을 점검합니다.

# 임계치
주요 서비스 포트 connected 상태 유지

# 판단기준
- **양호**: 운영에 필요한 모든 인터페이스가 정상적으로 connected 상태임
- **경고**: 주요 인터페이스가 비정상적으로 Down(notconnect) 되거나 속도/Duplex 협상 실패
- **확인 필요**: 명령어 실행 실패, 수집된 출력 결과와 포맷이 다르거나 확인이 불가능한 상태
