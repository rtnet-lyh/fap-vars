# 영역
LOG

# 세부 점검 항목
커널/부팅 이상 이벤트 로그

# 점검 내용
윈도우에서 리눅스의 `kernel panic`에 대응하는 장애성 이벤트만 추려 검색합니다.
BugCheck, Kernel-Power 41, EventLog 6008, LiveKernelEvent/BlueScreen 계열을 중심으로 확인합니다.

# 구분
필수

# 명령어
```powershell
$OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); $events=Get-WinEvent -FilterHashtable @{LogName=@('System','Application'); StartTime=(Get-Date).AddDays(-30)} -ErrorAction SilentlyContinue | Where-Object { ($_.ProviderName -eq 'Microsoft-Windows-Kernel-Power' -and $_.Id -eq 41) -or ($_.ProviderName -eq 'EventLog' -and $_.Id -eq 6008) -or ($_.ProviderName -match 'BugCheck|Microsoft-Windows-WER-SystemErrorReporting|Windows Error Reporting' -and $_.Message -match '(?i)bugcheck|blue ?screen|livekernelevent|kernel panic|system error') -or ($_.Message -match '(?i)bugcheck|blue ?screen|livekernelevent|kernel panic') } | Sort-Object TimeCreated -Descending | Select-Object -First 100 @{N='TimeCreated';E={$_.TimeCreated.ToString('yyyy-MM-dd HH:mm:ss')}},LogName,ProviderName,Id,LevelDisplayName,@{N='Message';E={($_.Message -replace '\r?\n',' ')}}; if($events){$events | ConvertTo-Json -Depth 4 -Compress}else{'[]'}
```

# 출력 결과
```json
[{"TimeCreated":"2026-04-10 07:11:20","LogName":"System","ProviderName":"Microsoft-Windows-Kernel-Power","Id":41,"LevelDisplayName":"Critical","Message":"The system has rebooted without cleanly shutting down first."}]
```

# 설명
- 절전/재개 정보성 이벤트(`Kernel-Power 42/107/187`)는 제외합니다.
- 비정상 종료, 블루스크린, BugCheck, LiveKernelEvent 같은 실제 장애성 징후만 집계합니다.
- 콜 트레이스와 CPU/프로세스 세부 정보는 일반 이벤트 로그에 충분히 남지 않으므로, 이벤트가 확인되면 메모리 덤프 분석이 필요합니다.

# 임계치
- `max_panic_like_event_count`: `0`
- `failure_keywords`: 없음

# 판단기준
- **정상**: BugCheck, Kernel-Power 41, EventLog 6008, LiveKernelEvent 계열 이벤트 수가 허용 범위 이내입니다.
- **경고**: 장애성 이벤트가 임계치를 초과하면 불량으로 판단하고, 재부팅 후 상태 점검 및 덤프 분석을 권고합니다.


