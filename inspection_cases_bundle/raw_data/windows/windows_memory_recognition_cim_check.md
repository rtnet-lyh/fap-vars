# 영역
MEMORY

# 세부 점검항목
메모리 상태 확인

# 점검 내용
Windows CIM 기준 물리 메모리 모듈 및 총 용량 확인

# 구분
필수

# 명령어
```powershell
$ErrorActionPreference = 'Stop'; $mem = Get-CimInstance Win32_PhysicalMemory | Select-Object BankLabel, DeviceLocator, Capacity, Speed, Manufacturer, PartNumber; $total = ($mem | Measure-Object -Property Capacity -Sum).Sum; [pscustomobject]@{ dimm_count = @($mem).Count; total_physical_memory_bytes = [int64]$total; modules = $mem } | ConvertTo-Json -Compress -Depth 6
```

# 출력 결과
```json
{"dimm_count":2,"total_physical_memory_bytes":17179869184,"modules":[{"BankLabel":"BANK 0","DeviceLocator":"DIMM 0","Capacity":8589934592,"Speed":2666,"Manufacturer":"Demo","PartNumber":"DEMO"}]}
```

# 설명
- Win32_PhysicalMemory로 물리 메모리 모듈과 총 용량을 확인한다.
- 모듈 수 또는 총 용량이 확인되지 않으면 메모리 인식 상태와 하드웨어 이벤트를 추가 확인한다.

# 임계치
없음

# 판단기준
- **양호**: 물리 메모리 모듈과 총 용량이 확인되는 경우
- **경고**: 모듈 또는 총 용량이 확인되지 않는 경우
