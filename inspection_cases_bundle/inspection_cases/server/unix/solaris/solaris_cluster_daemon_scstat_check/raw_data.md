# 영역
CLUSTER

# 세부 점검항목
Cluster 정상 유무 점검

# 점검 내용
Solaris Cluster의 노드, 전송 경로, 리소스 그룹, 네트워크 인터페이스 상태를 `scstat`으로 점검합니다.

# 구분
필수

# 명령어
```bash
scstat
```

# 출력 결과
```text
=== Cluster Nodes ===
node1  Online
node2  Online

=== Cluster Transport Paths ===
node1 -> node2  Path online
node2 -> node1  Path online

=== Resource Groups ===
resource_grp1  node1  Online
resource_grp2  node2  Online

=== Network Interfaces ===
net0  node1  Online
net1  node2  Online
```

# 설명
- Cluster Nodes, Transport Paths, Resource Groups, Network Interfaces 상태를 확인합니다.
- `Offline`, `Maintenance`, `Path down` 상태가 있으면 즉시 점검이 필요합니다.
- `scstat` 출력에서 필수 섹션이 누락되면 파싱 실패로 처리합니다.
- `장치를 찾을 수 없습니다`, `module`, `not found` 같은 실행 오류 문구도 실패로 처리합니다.

# 임계치
- `bad_status_keywords`: `offline,maintenance,path down`
- `failure_keywords`: `장치를 찾을 수 없습니다,not found,module,cannot,command not found`
- `required_sections`: `Cluster Nodes,Cluster Transport Paths,Resource Groups,Network Interfaces`

# 판단기준
- **정상**: 필수 섹션이 모두 존재하고 `Offline`, `Maintenance`, `Path down` 상태가 없는 경우
- **실패**: 노드, 경로, 리소스 그룹, 인터페이스 중 하나라도 비정상 상태가 확인되는 경우
- **실패**: `scstat` 명령 실행 실패, 실행 오류 문구 확인, 출력 비어 있음, 필수 섹션 누락 또는 파싱 실패 시
