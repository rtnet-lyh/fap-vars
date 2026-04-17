# 영역
CLUSTER

# 세부 점검항목
Cluster 데몬 상태

# 점검 내용
Cluster 정상 유무 점검(클러스터의 데몬 Maintenance/Offline 점검)

# 구분
권고

# 명령어
```bash
crm_mon -1
```

# 출력 결과
```text
Stack: corosync
Current DC: node1 (version 2.1.6-9.el8) - partition with quorum
Last updated: Mon Apr 13 10:15:22 2026
Last change:  Mon Apr 13 10:10:01 2026 by hacluster via crmd on node1

2 nodes configured
3 resource instances configured

Node List:
  * Online: [ node1 node2 ]

Full List of Resources:
  * vip_1     (ocf::heartbeat:IPaddr2):       Started node1
  * web_srv   (systemd:httpd):                Started node1
  * Clone Set: ping-clone [ping]
    * Started: [ node1 node2 ]

Daemon Status:
  corosync: active/enabled
  pacemaker: active/enabled
  pcsd: active/enabled
```

# 설명
- `crm_mon -1` 명령은 Pacemaker/Corosync 클러스터의 현재 상태를 1회 출력하여 노드, 리소스, 데몬 상태를 확인하는 명령이다.
- `Node List`에서 `Online` 노드 목록과 `OFFLINE` 또는 `Offline` 노드 존재 여부를 확인한다. Offline 노드가 있으면 클러스터 구성원 일부가 정상 참여하지 못하는 상태이므로 장애로 판단한다.
- `Daemon Status`에서 `corosync`, `pacemaker`, `pcsd`가 `active/enabled` 상태인지 확인한다. 데몬이 inactive, disabled, failed 상태이면 클러스터 통신, 리소스 제어, PCS 관리 기능에 문제가 있을 수 있다.
- Maintenance 모드가 표시되는 경우 계획된 작업 여부를 확인한다. 계획되지 않은 Maintenance 상태라면 리소스 자동 복구나 이동이 제한될 수 있으므로 운영자 확인이 필요하다.
- `crm_mon` 명령이 존재하지 않으면 해당 서버는 Pacemaker 클러스터 패키지가 설치되지 않았거나 클러스터 미구성 대상일 수 있으므로 본 항목에서는 성공으로 판단한다.

# 임계치
없음

# 판단기준
- **성공**: `crm_mon` 명령이 존재하지 않아 클러스터 미구성 서버로 판단되는 경우
- **성공**: `crm_mon -1` 결과에서 Offline 노드가 확인되지 않는 경우
- **실패**: `crm_mon -1` 결과에서 Offline 노드가 하나 이상 확인되는 경우
- **참고**: Maintenance 상태가 확인되면 계획된 유지보수 여부를 별도로 확인한다. 본 항목의 실패 기준은 Offline 노드 존재 여부를 우선 적용한다.
