# 영역
NETWORK

# 세부 점검항목
NW 링크 상태 연결속도 설정

# 점검 내용
`dladm show-phys` 출력으로 물리 네트워크 링크의 연결 상태, 속도, duplex 설정이 운영 기준과 일치하는지 점검합니다.

# 구분
필수

# 명령어
```bash
dladm show-phys
```

# 출력 결과
```text
LINK     MEDIA      STATE    SPEED   DUPLEX
e1000g0  1000baseT  up       1000    full
e1000g1  1000baseT  down     1000    full
e1000g2  1000baseT  unknown  1000    full
```

# 설명
- `STATE`는 `up`이어야 정상입니다.
- `down` 또는 `unknown`이면 인터페이스, 케이블, 설정 점검이 필요합니다.
- `SPEED`, `DUPLEX`가 운영 기준값과 일치하는지 함께 확인합니다.
- `장치를 찾을 수 없습니다`, `module`, `not found`, `command not found` 같은 실행 오류 문구도 실패로 처리합니다.

# 임계치
- `required_state`: `up`
- `expected_speed_map`: `e1000g0:1000,e1000g1:1000,e1000g2:1000`
- `expected_duplex_map`: `e1000g0:full,e1000g1:full,e1000g2:full`
- `failure_keywords`: `장치를 찾을 수 없습니다,not found,module,cannot,command not found,no such file`

# 판단기준
- **정상**: 모든 링크의 `STATE`가 `up`이고 필요한 링크별 `SPEED`, `DUPLEX`도 기준과 일치하는 경우
- **실패**: 하나라도 `STATE`가 `down` 또는 `unknown` 등 기준과 다른 경우
- **실패**: 링크별 속도 또는 duplex 설정이 기준과 다르거나 숫자 파싱에 실패한 경우
- **실패**: `dladm show-phys` 명령 실행 실패, 실행 오류 문구 확인, `stderr` 출력 확인 시
