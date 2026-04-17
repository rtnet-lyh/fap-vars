# 영역
CLUSTER

# 세부 점검항목
Cluster 데몬 상태

# 점검 내용
Serviceguard 클러스터 및 패키지의 정상 동작 여부를 점검한다.

# 구분
권고

# 명령어
```bash
cmviewcl -v
```

# 출력 결과
```text
CLUSTER      STATUS
sgcluster    up

  NODE        STATUS       STATE
  node1       up           running
  node2       up           running

  PACKAGE     STATUS       STATE       AUTO_RUN
  pkg_app     up           running     enabled
```

# 설명
- `cmviewcl -v` 명령으로 HP Serviceguard 클러스터, 노드, 패키지 상태를 확인한다.
- 클러스터와 모든 운영 대상 노드가 `up` 또는 `running` 상태이면 정상으로 본다.
- 패키지가 `down`, `halted`, `unknown` 상태이거나 노드 상태가 비정상이면 서비스 이중화에 문제가 있을 수 있다.
- Serviceguard 미구성 서버는 해당 항목을 적용 제외 또는 확인 필요로 분류한다.

# 임계치
expected_cluster_status
expected_package_status

# 판단기준
- **양호**: 클러스터, 노드, 패키지가 모두 `up` 또는 `running` 상태인 경우
- **경고**: 운영 대상 노드 또는 패키지가 `down`, `halted`, `unknown` 등 비정상 상태인 경우
- **확인 필요**: Serviceguard가 설치되지 않았거나 클러스터 미구성 서버인 경우
