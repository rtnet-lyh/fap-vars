# 영역
CPU

# 세부 점검항목
CPU 사용률

# 점검 내용
Windows 성능 카운터 기준 CPU 사용률 확인

# 구분
권고

# 명령어
```powershell
$ErrorActionPreference = 'Stop'; $sample = Get-Counter '\Processor(_Total)\% Processor Time'; $value = [math]::Round($sample.CounterSamples[0].CookedValue, 2); [pscustomobject]@{ cpu_usage_percent = $value } | ConvertTo-Json -Compress -Depth 6
```

# 출력 결과
```json
{"cpu_usage_percent":12.5}
```

# 설명
- Get-Counter 성능 카운터로 전체 CPU 사용률을 조회한다.
- CPU 사용률이 임계치보다 높으면 프로세스 부하, 스케줄링 지연, 서비스 성능 저하 가능성이 있어 원인 프로세스 확인이 필요하다.

# 임계치
max_cpu_usage_percent: 80

# 판단기준
- **양호**: CPU 사용률이 임계치 이하인 경우
- **경고**: CPU 사용률이 임계치를 초과한 경우
