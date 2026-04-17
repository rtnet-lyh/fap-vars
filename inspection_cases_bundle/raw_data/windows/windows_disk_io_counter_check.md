# 영역
DISK

# 세부 점검항목
Disk I/O 점검

# 점검 내용
Windows 성능 카운터 기준 Disk I/O 지연 확인

# 구분
권고

# 명령어
```powershell
$ErrorActionPreference = 'Stop'; $read = (Get-Counter '\PhysicalDisk(_Total)\Avg. Disk sec/Read').CounterSamples[0].CookedValue; $write = (Get-Counter '\PhysicalDisk(_Total)\Avg. Disk sec/Write').CounterSamples[0].CookedValue; [pscustomobject]@{ avg_disk_sec_read = [math]::Round($read, 4); avg_disk_sec_write = [math]::Round($write, 4) } | ConvertTo-Json -Compress -Depth 6
```

# 출력 결과
```json
{"avg_disk_sec_read":0.001,"avg_disk_sec_write":0.002}
```

# 설명
- PhysicalDisk 성능 카운터의 Avg. Disk sec/Read, Avg. Disk sec/Write 값을 확인한다.
- 평균 지연 시간이 임계치를 초과하면 스토리지 경로, 디스크 상태, I/O 부하를 추가 점검한다.

# 임계치
max_avg_disk_sec: 0.02

# 판단기준
- **양호**: Read/Write 평균 지연 시간이 임계치 이하인 경우
- **경고**: Read 또는 Write 평균 지연 시간이 임계치를 초과한 경우
