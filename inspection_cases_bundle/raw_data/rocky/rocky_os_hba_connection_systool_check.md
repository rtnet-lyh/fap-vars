# 영역
OS

# 세부 점검항목
HBA 연결상태 점검

# 점검 내용
HBA 연결 정상 유무 점검(State Online, Current Speed)

# 구분
권고

# 명령어
```bash
systool -c fc_host -a
```

# 출력 결과
```text
Class Device = "host0"
Class Device path = "/sys/class/fc_host/host0"
port_name = "0x50014380186baf12"
node_name = "0x50014380186baf10"
port_state = "Online"
speed = "8 Gbit"
supported_speeds = "4 Gbit, 8 Gbit, 16 Gbit"
```

# 설명
- `systool -c fc_host -a` 명령은 Fibre Channel HBA 포트의 연결 상태를 조회할 때 사용한다.
- PDF의 `fc_portname`, `fc_node_name`, `fc_state`, `fc_speed`는 Linux `systool` 출력의 `port_name`, `node_name`, `port_state`, `speed`와 같은 의미로 해석한다.
- `port_state = "Online"`이면 HBA 포트가 정상적으로 링크 업 상태이며 스토리지 패브릭에 연결된 것으로 본다.
- `speed = "8 Gbit"` 같은 값은 현재 협상된 링크 속도를 의미한다. 기대 속도보다 낮거나 `unknown`으로 표시되면 SFP, 케이블, 스위치 포트, HBA 설정을 함께 점검한다.
- `supported_speeds`는 해당 포트가 지원하는 최대 속도 목록이다. 현재 속도와 지원 속도 차이가 크면 링크 협상이나 패브릭 설정 문제 가능성을 확인한다.
- `Offline`, `Linkdown`, `Unknown` 상태가 보이면 HBA 포트, 광 모듈, 케이블, SAN 스위치, 스토리지 연결 구성을 점검한다.

# 임계치
없음

# 판단기준
- **양호**: `systool -c fc_host -a` 결과에서 HBA 포트가 확인되고 `port_state`가 `Online`이며 현재 속도 값이 정상적으로 표시되는 경우
- **경고**: 포트 상태는 `Online`이지만 현재 속도 값이 비정상적으로 낮거나 `unknown`으로 표시되어 추가 확인이 필요한 경우
- **실패**: HBA 포트 상태가 `Offline`, `Linkdown`, `Unknown` 등 비정상 상태로 표시되는 경우
- **참고**: `fc_host` 클래스 자체가 없으면 FC HBA가 미구성 상태이거나 관련 패키지/드라이버가 없을 수 있으므로 서버 스토리지 연결 구조를 먼저 확인한다
