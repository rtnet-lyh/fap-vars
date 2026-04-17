# 영역
LOG

# 세부 점검 항목
클러스터 관련 이벤트 로그

# 점검 내용
최근 이벤트 로그에서 Failover Clustering 관련 오류/경고 이벤트를 검색합니다.

# 구분
필수

# 명령어
```powershell
if(Get-WinEvent -ListLog 'Microsoft-Windows-FailoverClustering/Operational' -ErrorAction SilentlyContinue){Get-WinEvent -FilterHashtable @{LogName='Microsoft-Windows-FailoverClustering/Operational'; StartTime=(Get-Date).AddDays(-30)} -ErrorAction SilentlyContinue | Where-Object { $_.Message -match '(?i)cluster|resource status|unknown|offline|online|error' } | Select-Object -First 100 TimeCreated,Id,LevelDisplayName,@{N='Message';E={($_.Message -replace '\\r?\\n',' ')}} | Format-Table -Wrap -Auto}else{'Failover Clustering log not present on this PC (Windows 11 is typically not a local WSFC node).'}
```

# 출력 결과
```text
TimeCreated           ProviderName         Id   Level     Message
2026-04-10 오전 09:10:01  FailoverClustering  1234 Warning   Cluster network interface issue...
```

# 설명
- 클러스터 서비스, 노드 통신, 리소스 이동 실패 등과 관련된 이벤트를 확인합니다.
- 허용된 이벤트 수를 초과하면 이상으로 판단합니다.

# 임계치
- `max_cluster_event_count`: `0`
- `failure_keywords`: 없음

# 판단기준
- **정상**: 검색된 클러스터 관련 이벤트 수가 허용 범위 이내입니다.
- **대상 아님**: 클러스터 기능이 없는 일반 Windows 11 환경입니다.
- **경고**: 클러스터 관련 오류/경고 이벤트 수가 임계치를 초과합니다.


