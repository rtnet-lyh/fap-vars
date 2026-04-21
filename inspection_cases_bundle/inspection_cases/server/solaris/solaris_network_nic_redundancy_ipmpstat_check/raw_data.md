# 영역
NETWORK

# 세부 점검항목
NIC 이중화(IPMP) 및 Daemon 상태 점검

# 점검 내용
Solaris 서버의 IPMP 그룹 내 NIC 이중화 상태와 각 인터페이스의 활성/링크/상태 값을 점검합니다.

# 구분
필수

# 명령어
```bash
ipmpstat -i
```

# 출력 결과
```text
INTERFACE ACTIVE GROUP FLAGS  LINK STATE
net0      yes    ipmp0 ------ up   ok
net1      yes    ipmp0 ------ up   ok
```

# 설명
- `ipmpstat -i`는 IPMP 인터페이스별 ACTIVE, GROUP, LINK, STATE 값을 확인할 때 사용합니다.
- 같은 IPMP 그룹 내 인터페이스가 2개 이상이고, 각 인터페이스의 `ACTIVE=yes`, `LINK=up`, `STATE=ok`이면 정상으로 판단합니다.
- `off-line`, `failed`, `down`, `unknown` 등 비정상 상태가 있거나 그룹 내 인터페이스 수가 부족하면 실패로 처리합니다.
- `ipmpstat` 명령이 없거나 출력 형식을 해석할 수 없으면 실패로 처리합니다.

# 임계치
- `min_group_interface_count`: `2`
- `expected_active_value`: `yes`
- `expected_link_value`: `up`
- `expected_state_value`: `ok`
- `failure_keywords`: 없음

# 판단기준
- **정상**: 각 IPMP 그룹에 인터페이스가 2개 이상 존재하고 모든 인터페이스가 `ACTIVE=yes`, `LINK=up`, `STATE=ok`인 경우
- **실패**: 그룹 내 인터페이스 수가 부족하거나, `ACTIVE`, `LINK`, `STATE` 중 하나라도 기준과 다른 경우
- **실패**: `ipmpstat` 명령 실행 실패, 명령 미설치, 출력 파싱 실패, 오류 로그 확인 시
