# 영역
CLUSTER

# 세부 점검 항목
WSFC 클러스터 노드 및 리소스 상태

# 점검 내용
FailoverClusters 모듈 가용성, 클러스터 연결 여부, 온라인 노드 수와 리소스 온라인 상태를 점검합니다.

# 구분
필수

# 명령어
```powershell
$OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); if(Get-Module -ListAvailable -Name FailoverClusters){Import-Module FailoverClusters -ErrorAction SilentlyContinue; $cl='.'; try{$c=if($cl -eq '.'){Get-Cluster -ErrorAction Stop}else{Get-Cluster -Name $cl -ErrorAction Stop}; $n=Get-ClusterNode -Cluster $cl -ErrorAction Stop; $r=Get-ClusterResource -Cluster $cl -ErrorAction Stop; $result=[ordered]@{Summary=[ordered]@{Cluster=$c.Name; NodesConfigured=$n.Count; NodesOnline=($n|Where-Object State -eq 'Up').Count; ResourceInstancesConfigured=$r.Count; ResourcesOnline=($r|Where-Object State -eq 'Online').Count}; Nodes=@($n|Select-Object Name,Id,State); Resources=@($r|Select-Object Name,State,ResourceType,OwnerGroup,OwnerNode); FenceHistory='N/A (no direct crm_mon-style fencing history field in WSFC PowerShell)'}; $result|ConvertTo-Json -Depth 4} catch {'Failover cluster not found/reachable. For remote WSFC, change $cl=''.'' to your cluster name.'}} else {'FailoverClusters module not installed. On Windows 11, install RSAT Failover Clustering Tools first.'}
```

# 출력 결과
```json
{
  "Summary": {
    "Cluster": "WSFC01",
    "NodesConfigured": 2,
    "NodesOnline": 2,
    "ResourceInstancesConfigured": 5,
    "ResourcesOnline": 5
  },
  "Nodes": [
    {
      "Name": "NODE01",
      "Id": 1,
      "State": "Up"
    },
    {
      "Name": "NODE02",
      "Id": 2,
      "State": "Up"
    }
  ],
  "Resources": [
    {
      "Name": "Cluster IP Address",
      "State": "Online",
      "ResourceType": "IP Address",
      "OwnerGroup": "Cluster Group",
      "OwnerNode": "NODE01"
    },
    {
      "Name": "Cluster Name",
      "State": "Online",
      "ResourceType": "Network Name",
      "OwnerGroup": "Cluster Group",
      "OwnerNode": "NODE01"
    }
  ],
  "FenceHistory": "N/A (no direct crm_mon-style fencing history field in WSFC PowerShell)"
}
```

# 설명
- RSAT Failover Clustering Tools가 설치되어 있으면 로컬 또는 지정한 WSFC 정보를 조회합니다.
- 노드 Down 수와 리소스 Offline 수를 기준으로 클러스터 가용성을 판단합니다.

# 임계치
- `max_down_node_count`: `0`
- `max_offline_resource_count`: `0`
- `failure_keywords`: 없음

# 판단기준
- **정상**: 허용된 범위 안에서 모든 노드와 주요 리소스가 온라인 상태입니다.
- **불량**: FailoverClusters 모듈이 없거나 WSFC에 연결할 수 없거나, Down 노드 수 또는 Offline 리소스 수가 임계치를 초과합니다.


