# 영역
HW 상태

# 세부 점검항목
VLAN 상태 점검

# 점검 내용
VLAN 상태 확인

# 구분
권고

# 명령어
```bash
show vsan
```

# 출력 결과
```text
CITS-SAN1# show vsan
vsan 1 information
         name:VSAN0001  state:active
         interoperability mode:default
         loadbalancing:src-id/dst-id/oxid
         operational state:down

vsan 10 information
         name:VSAN0010  state:active
         interoperability mode:default
         loadbalancing:src-id/dst-id/oxid
         operational state:up

vsan 4079:evfp_isolated_vsan

vsan 4094:isolated_vsan

```

# 설명
- 명령어: 장비에 구성된 VSAN목록과 각 VSAN의 상태를 확인하는 명령어.
- 운영대상 VSAN의 state가 active 이면 정상 사용가능 상태.
- 운영대상 VSAN 리스트를 호스트 변수로 받아와야함.

[참고]
- VLAN 명령어를 사용해야하지만 해당 장비는 VLAN을 지원하지않는 장비로 VSAN으로 대체 점검함.
- 운영대상 VSAN 목록을 변수로 정의 하기 힘든 환경에서는 담당자확인필요 처리.

# 임계치
active_vsan
- 운영대상 VSAN 목록 변수로 설정

# 판단기준
- **양호**: `active_vsan`에 포함된 VSAN의 state 값이 active인 경우
- **경고**: `active_vsan`에 포함된 VSAN의 state 값이 active가 아닌 경우
- **확인 필요**: 명령어 실패 및 `active_vsan` 변수 미 선언, 파싱 불가