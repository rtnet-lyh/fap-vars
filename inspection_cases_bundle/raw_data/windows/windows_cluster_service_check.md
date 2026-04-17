# 영역
CLUSTER

# 세부 점검항목
Cluster 데몬 상태

# 점검 내용
Failover Cluster 서비스(ClusSvc) 실행 상태 확인

# 구분
필수

# 명령어
```powershell
$ErrorActionPreference = 'Stop'; $svc = Get-Service -Name ClusSvc -ErrorAction SilentlyContinue; $status = if ($svc) { $svc.Status.ToString() } else { '' }; $startType = if ($svc) { $svc.StartType.ToString() } else { '' }; [pscustomobject]@{ service_exists = [bool]$svc; service_status = $status; service_start_type = $startType } | ConvertTo-Json -Compress -Depth 6
```

# 출력 결과
```json
{"service_exists":true,"service_status":"Running","service_start_type":"Automatic"}
```

# 설명
- ClusSvc 서비스 존재 여부와 실행 상태를 확인한다.
- Failover Cluster 대상에서 서비스가 Running이 아니면 클러스터 장애 가능성이 있어 즉시 확인한다.

# 임계치
없음

# 판단기준
- **양호**: ClusSvc 서비스가 Running 상태인 경우
- **대상미해당**: Failover Cluster 서비스가 없는 경우
- **경고**: ClusSvc 서비스가 Running이 아닌 경우
