# 영역
MEMORY

# 세부 점검항목
메모리 사용률

# 점검 내용
Windows CIM 기준 메모리 사용률 확인

# 구분
권고

# 명령어
```powershell
$ErrorActionPreference = 'Stop'; $os = Get-CimInstance Win32_OperatingSystem; $total = [double]$os.TotalVisibleMemorySize; $free = [double]$os.FreePhysicalMemory; $usedPercent = if ($total -gt 0) { [math]::Round((($total - $free) / $total) * 100, 2) } else { 0 }; [pscustomobject]@{ total_memory_kib = [int64]$total; free_memory_kib = [int64]$free; memory_usage_percent = $usedPercent } | ConvertTo-Json -Compress -Depth 6
```

# 출력 결과
```json
{"total_memory_kib":16777216,"free_memory_kib":8388608,"memory_usage_percent":50.0}
```

# 설명
- Win32_OperatingSystem의 TotalVisibleMemorySize와 FreePhysicalMemory로 메모리 사용률을 계산한다.
- 메모리 사용률이 임계치를 초과하면 불필요한 프로세스 종료 또는 메모리 증설 검토가 필요하다.

# 임계치
max_memory_usage_percent: 80

# 판단기준
- **양호**: 메모리 사용률이 임계치 이하인 경우
- **경고**: 메모리 사용률이 임계치를 초과한 경우
