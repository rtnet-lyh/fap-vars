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
show vlans
```

# 출력 결과
```text
falcon@Center_Server_J4300_A> show vlans

Routing instance        VLAN name             Tag          Interfaces
default-switch          default               1
                                                           xe-0/0/35.0*
default-switch          v808                  808
                                                           ge-0/0/0.0*
                                                           ge-0/0/1.0*
                                                           ge-0/0/10.0*
                                                           ge-0/0/11.0*

```

# 설명
- 명령어: 장비에 구성된 VLAN 정보를 확인하는 명령어.
- VLAN상태는 해당 명령어 사용 시 사용하는 VLAN이 존재하는 지 여부로 판단 할 수 있음.


[참고]
- 운영대상 VLAN 목록을 변수로 정의 하기 힘든 환경에서는 담당자확인필요 처리.

# 임계치
active_vlan_name
- 운영대상 VLAN name

# 판단기준
- **양호**: VLAN name에 `active_vlan_name`에 포함된 경우
- **경고**: VLAN name에 `active_vlan_name`에 포함되지 않은 경우
- **확인 필요**: 명령어 실패 및 파싱 불가