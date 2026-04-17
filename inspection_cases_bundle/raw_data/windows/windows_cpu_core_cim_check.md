# 영역
CPU

# 세부 점검항목
코어별 상태 점검

# 점검 내용
CPU 코어 및 논리 프로세서 인식 상태 확인

# 구분
필수

# 명령어
```powershell
$ErrorActionPreference = 'Stop'; $cpus = Get-CimInstance Win32_Processor | Select-Object Name, NumberOfCores, NumberOfLogicalProcessors, LoadPercentage, Status; $logical = ($cpus | Measure-Object -Property NumberOfLogicalProcessors -Sum).Sum; $physical = ($cpus | Measure-Object -Property NumberOfCores -Sum).Sum; $bad = @($cpus | Where-Object { $_.Status -and $_.Status -ne 'OK' }); [pscustomobject]@{ processor_count = @($cpus).Count; physical_core_count = [int]$physical; logical_processor_count = [int]$logical; abnormal_processor_count = @($bad).Count; processors = $cpus } | ConvertTo-Json -Compress -Depth 6
```

# 출력 결과
```json
{"processor_count":1,"physical_core_count":4,"logical_processor_count":8,"abnormal_processor_count":0,"processors":[{"Name":"Intel(R) Xeon(R)","NumberOfCores":4,"NumberOfLogicalProcessors":8,"LoadPercentage":12,"Status":"OK"}]}
```

# 설명
- Win32_Processor CIM 정보로 물리 코어와 논리 프로세서 수를 확인한다.
- 논리 프로세서 수가 0이거나 Status가 OK가 아니면 CPU 인식 또는 상태 확인이 필요하다.

# 임계치
없음

# 판단기준
- **양호**: CPU 코어와 논리 프로세서가 정상 인식되고 Status가 OK인 경우
- **주의**: Status가 OK가 아닌 프로세서 항목이 확인되는 경우
- **경고**: 논리 CPU 수가 0으로 표시되는 경우
