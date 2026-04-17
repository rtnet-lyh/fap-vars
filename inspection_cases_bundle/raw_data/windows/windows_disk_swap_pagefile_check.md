# 영역
DISK

# 세부 점검항목
Disk Swap 사용률

# 점검 내용
Windows PageFile 사용률 확인

# 구분
권고

# 명령어
```powershell
$ErrorActionPreference = 'Stop'; $page = Get-CimInstance Win32_PageFileUsage | Select-Object Name, AllocatedBaseSize, CurrentUsage, PeakUsage; $allocated = ($page | Measure-Object -Property AllocatedBaseSize -Sum).Sum; $current = ($page | Measure-Object -Property CurrentUsage -Sum).Sum; $usage = if ($allocated -gt 0) { [math]::Round(($current / $allocated) * 100, 2) } else { 0 }; [pscustomobject]@{ pagefile_count = @($page).Count; allocated_mb = [int64]$allocated; current_usage_mb = [int64]$current; pagefile_usage_percent = $usage; pagefiles = $page } | ConvertTo-Json -Compress -Depth 6
```

# 출력 결과
```json
{"pagefile_count":1,"allocated_mb":4096,"current_usage_mb":512,"pagefile_usage_percent":12.5,"pagefiles":[{"Name":"C:\\pagefile.sys","AllocatedBaseSize":4096,"CurrentUsage":512,"PeakUsage":1024}]}
```

# 설명
- Win32_PageFileUsage로 디스크 기반 PageFile 사용률을 조회한다.
- 사용률이 임계치를 초과하면 메모리 압박과 디스크 I/O 증가 가능성이 있어 추가 확인이 필요하다.

# 임계치
max_pagefile_usage_percent: 50

# 판단기준
- **양호**: PageFile 사용률이 임계치 이하인 경우
- **주의**: PageFile 항목이 확인되지 않아 운영 정책 확인이 필요한 경우
- **경고**: PageFile 사용률이 임계치를 초과한 경우
