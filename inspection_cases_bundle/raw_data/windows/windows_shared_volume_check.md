# 영역
CLUSTER

# 세부 점검항목
공유 볼륨 상태 점검

# 점검 내용
Failover Cluster Shared Volume 조회 및 상태 확인

# 구분
필수

# 명령어
```powershell
$ErrorActionPreference = 'Stop'; $available = [bool](Get-Command Get-ClusterSharedVolume -ErrorAction SilentlyContinue); $csv = @(); if ($available) { $csv = @(Get-ClusterSharedVolume | Select-Object Name, State, OwnerNode) }; [pscustomobject]@{ cluster_shared_volume_available = $available; csv_count = @($csv).Count; csv = $csv } | ConvertTo-Json -Compress -Depth 6
```

# 출력 결과
```json
{"cluster_shared_volume_available":true,"csv_count":1,"csv":[{"Name":"Cluster Disk 1","State":"Online","OwnerNode":"WIN-DEMO"}]}
```

# 설명
- Get-ClusterSharedVolume으로 CSV 조회 가능 여부와 볼륨 상태를 확인한다.
- Failover Cluster 모듈 또는 CSV 구성이 없으면 대상미해당으로 처리하고, 클러스터 대상이면 수동 확인한다.

# 임계치
없음

# 판단기준
- **양호**: Cluster Shared Volume 조회가 정상 수행되는 경우
- **대상미해당**: Failover Cluster 모듈 또는 CSV 구성이 없는 경우
