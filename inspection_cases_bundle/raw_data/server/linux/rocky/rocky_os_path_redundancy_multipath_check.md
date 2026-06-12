# 영역
DISK

# 세부 점검항목
Path 이중화 점검

# 점검 내용
Multipath 이중화 정상 유무 점검(CONNECTED 등 상태 확인)

# 구분
권고

# 명령어
```bash
multipath -ll
```

# 출력 결과
```text
mpatha (36005076810810548b8000000000000aa) dm-2 IBM,2145
size=100G features='1 queue_if_no_path' hwhandler='0' wp=rw
|-+- policy='round-robin 0' prio=1 status=active
| `- 2:0:0:1 sdb 8:16 active ready running
`-+- policy='round-robin 0' prio=1 status=enabled
  `- 3:0:0:1 sdc 8:32 active ready running
```

# 설명
- `multipath -ll` 명령은 스토리지 장치에 대해 구성된 다중 경로(Multipath) 상태를 확인할 때 사용한다.
- 예시의 `sdb`, `sdc` 같은 장치는 실제 스토리지에 연결된 물리 경로를 나타내며, 괄호의 `8:16`, `8:32` 값은 Linux 블록 디바이스 번호다.
- `status=active`는 현재 실제 I/O를 처리하는 활성 경로 그룹을 의미하고, `status=enabled`는 대기 중이지만 장애 시 활성 경로로 전환될 수 있는 사용 가능한 경로 그룹을 의미한다.
- 각 경로 라인의 `active ready running`은 해당 경로가 인식되어 정상적으로 I/O를 처리할 수 있는 상태임을 의미한다.
- `policy='round-robin 0'`는 일반적인 경로 전환 정책 예시이며, 운영 환경에서 사용 중인 경로 정책이 일관되게 적용되어 있는지 함께 확인한다.
- `failed`, `faulty`, `offline` 같은 상태가 보이면 경로 장애 가능성이 있으므로 HBA, 케이블, SAN 스위치, 스토리지 포트 상태를 함께 점검한다.

# 임계치
없음

# 판단기준
- **양호**: `multipath -ll` 결과에서 경로 그룹 상태가 `active` 또는 `enabled`이고, 각 물리 경로가 `running` 상태로 확인되는 경우
- **경고**: `multipath -ll` 명령은 실행되지만 멀티패스 장치가 없거나, 경로 상태를 충분히 확인할 수 없어 실제 구성 여부를 추가 확인해야 하는 경우
- **실패**: `multipath -ll` 결과에 `failed`, `faulty`, `offline` 등 비정상 경로 상태가 하나 이상 확인되는 경우
- **참고**: SAN 다중 경로를 사용하지 않는 서버는 로컬 디스크 전용 구성일 수 있으므로 스토리지 연결 구조를 먼저 확인한다
