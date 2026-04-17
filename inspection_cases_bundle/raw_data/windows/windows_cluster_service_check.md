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
if(Get-Module -ListAvailable -Name FailoverClusters){Import-Module FailoverClusters -ErrorAction SilentlyContinue; $cl='.'; try{$c=if($cl -eq '.'){Get-Cluster -ErrorAction Stop}else{Get-Cluster -Name $cl -ErrorAction Stop}; $n=Get-ClusterNode -Cluster $cl -ErrorAction Stop; $r=Get-ClusterResource -Cluster $cl -ErrorAction Stop; '==Cluster Summary=='; [pscustomobject]@{Cluster=$c.Name; NodesConfigured=$n.Count; NodesOnline=($n|Where-Object State -eq 'Up').Count; ResourceInstancesConfigured=$r.Count; ResourcesOnline=($r|Where-Object State -eq 'Online').Count}|Format-List; '==Node List=='; $n|Select-Object Name,Id,State|Format-Table -Auto; '==Full List of Resources=='; $r|Select-Object Name,State,ResourceType,OwnerGroup,OwnerNode|Format-Table -Auto; '==Fence History=='; 'N/A (no direct crm_mon-style fencing history field in WSFC PowerShell)'} catch {'Failover cluster not found/reachable. For remote WSFC, change $cl=''.'' to your cluster name.'}} else {'FailoverClusters module not installed. On Windows 11, install RSAT Failover Clustering Tools first.'}
```

# 출력 결과
```text
==Cluster Summary==
Cluster : LAB-CLUSTER
NodesConfigured : 2
NodesOnline : 2
ResourceInstancesConfigured : 6
ResourcesOnline : 6

==Node List==
NODE01  1  Up
NODE02  2  Up
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
- **대상 아님**: FailoverClusters 모듈이 없거나 WSFC가 구성되지 않은 일반 Windows 11 환경입니다.
- **경고**: Down 노드 수 또는 Offline 리소스 수가 임계치를 초과합니다.


