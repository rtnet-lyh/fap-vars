# 영역
CLUSTER

# 세부 점검항목
서버 클러스터 노드 상태변경 발생 점검

# 점검 내용
Solaris 클러스터 로그에서 노드 online/offline 변경과 클러스터 통신 오류를 점검합니다.

# 구분
필수

# 명령어
```bash
clog | grep -i 'status change|offline|online|cluster error'
```

# 출력 결과
```text
[2024-09-16T10:00:00] Resource Status Change: Node1 Offline
[2024-09-16T10:05:00] Cluster Error: Node2 communication failure
[2024-09-16T10:10:00] Resource Status Change: Node3 Online
```

# 설명
- 노드 online/offline 변경 및 클러스터 통신 오류를 확인합니다.
- 노드 오프라인이나 통신 실패 메시지가 있으면 클러스터 상태 점검이 필요합니다.
- `online` 단독 상태 변경 로그는 정상 정보로 간주합니다.
- `grep` 특성상 일치 로그가 없으면 `rc=1`이 반환될 수 있으며, 이 경우는 정상으로 처리합니다.
- `장치를 찾을 수 없습니다`, `module`, `not found` 같은 실행 오류 문구도 실패로 처리합니다.

# 임계치
- `bad_log_keywords`: `offline,cluster error,communication failure,failed,failure`
- `failure_keywords`: `장치를 찾을 수 없습니다,not found,module,cannot,command not found`

# 판단기준
- **정상**: 클러스터 로그가 없거나 online 중심의 정상 정보만 있는 경우
- **실패**: `offline`, `cluster error`, `communication failure` 같은 비정상 로그가 확인되는 경우
- **실패**: `stderr`가 있거나 `clog | grep -i 'status change|offline|online|cluster error'` 명령 실행 실패 시
