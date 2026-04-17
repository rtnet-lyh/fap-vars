# 영역
로그

# 세부 점검항목
클러스터 로그

# 점검 내용
Serviceguard 클러스터 상태 변경과 통신 장애 로그를 점검한다.

# 구분
필수

# 명령어
```bash
tail -n 2000 /var/adm/cmcluster/cmcld.log | egrep -i 'status change|offline|online|unknown|cluster error|communication failure|error'
```

# 출력 결과
```text
Resource Status Change: node1 Offline
Cluster Error: node2 communication failure
```

# 설명
- Serviceguard `cmcld.log`에서 클러스터 상태 변경, 노드 offline, unknown, 통신 실패, 오류 로그를 확인한다.
- `status change online`처럼 정상 복구를 의미하는 메시지는 단독으로 불량으로 보지 않는다.
- `offline`, `unknown`, `cluster error`, `communication failure`, `error`가 확인되면 노드 상태, 네트워크, 패키지 상태를 함께 점검한다.
- Serviceguard 미구성 서버는 해당 항목을 적용 제외 또는 확인 필요로 분류한다.

# 임계치
cluster_bad_log_keywords
cluster_ignore_log_keywords

# 판단기준
- **양호**: 최근 Serviceguard 로그에 장애 키워드가 없거나 정상 online 메시지만 확인되는 경우
- **경고**: offline, unknown, cluster error, communication failure, error가 확인되는 경우
- **확인 필요**: 로그 파일이 없거나 Serviceguard 구성 여부가 불명확한 경우
