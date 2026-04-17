# 영역
DISK

# 세부 점검 항목
디스크 I/O Busy, Idle, Wait, Queue 길이

# 점검 내용
typeperf 기반 디스크 카운터를 이용해 Busy 비율, Idle 비율, 평균 대기시간, 큐 길이를 점검합니다.

# 구분
권고

# 명령어
```powershell
Get-CimInstance Win32_PerfFormattedData_PerfDisk_PhysicalDisk | Where-Object { $_.Name -ne '_Total' } | Select-Object @{N='device';E={$_.Name}},@{N='r/s';E={$_.DiskReadsPerSec}},@{N='w/s';E={$_.DiskWritesPerSec}},@{N='kr/s';E={[math]::Round($_.DiskReadBytesPerSec/1KB,2)}},@{N='kw/s';E={[math]::Round($_.DiskWriteBytesPerSec/1KB,2)}},@{N='wait(ms)';E={[math]::Round($_.AvgDiskSecPerTransfer*1000,2)}},@{N='actv';E={[math]::Round($_.AvgDiskQueueLength,2)}},@{N='%b';E={[math]::Round($_.PercentDiskTime,2)}},@{N='idle%';E={[math]::Round($_.PercentIdleTime,2)}} | Format-Table -Auto
```

# 출력 결과
```text
"(PDH-CSV 4.0)","\\HOST\\PhysicalDisk(_Total)\\% Disk Time","\\HOST\\PhysicalDisk(_Total)\\% Idle Time","\\HOST\\PhysicalDisk(_Total)\\Avg. Disk sec/Transfer","\\HOST\\PhysicalDisk(_Total)\\Current Disk Queue Length"
"04/10/2026 15:48:10.000","12.5","87.5","0.004","0.1"
```

# 설명
- Busy와 Idle은 전체 디스크 사용량, Wait는 전송당 평균 지연, Queue Length는 적체 수준을 의미합니다.
- 여러 지표를 함께 판단해 단순 사용률이 아닌 병목 여부를 봅니다.

# 임계치
- `max_busy_percent`: `80.0`
- `min_idle_percent`: `20.0`
- `max_wait_ms`: `10.0`
- `max_queue_length`: `1.0`
- `failure_keywords`: 없음

# 판단기준
- **정상**: Busy, Wait, Queue는 낮고 Idle은 충분합니다.
- **경고**: Busy 비율이 높거나 Idle이 낮거나 Wait/Queue가 임계치를 초과합니다.


