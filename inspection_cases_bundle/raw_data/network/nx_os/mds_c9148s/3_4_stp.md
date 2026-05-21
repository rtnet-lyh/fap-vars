# 영역
서비스

# 세부 점검항목
STP 상태 점검

# 점검 내용
STP 설정을 통해 Loop 구조를 방지하고 원활한 통신상태를 확인

# 구분
권고

# 명령어
```bash
show spannig-tree
```

# 출력 결과
```text
CITS-SAN1# show spannig-tree
                    ^
% Invalid command at '^' marker.

```

# 설명
- 명령어: Loop를 방지를 확인하는 명령어.
- Cisco SAN 장비에는 Fibre Channel Fabric 기반으로 동작하므로 Ethernet L2 스위치의 STP를 사용하지 않음.

# 임계치


# 판단기준
- **양호**: 점검 대상이 아님.
- **경고**: 점검 대상이 아님.
- **확인 필요**: 점검 대상이 아님.