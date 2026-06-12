# 영역
LOG

# 세부 점검 항목
전원 관련 이벤트 로그

# 점검 내용
전원 공급, 절전 복귀, 배터리/전원 오류와 관련된 이벤트를 검색합니다.

# 구분
필수

# 명령어
```powershell
$OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); $e=Get-WinEvent -FilterHashtable @{LogName='System';StartTime=(Get-Date).AddDays(-30);Level=@(1,2,3)} -ErrorAction SilentlyContinue | Where-Object { $_.ProviderName -in @('Microsoft-Windows-Kernel-Power','Microsoft-Windows-WHEA-Logger','Microsoft-Windows-Kernel-Boot','ACPI') -or $_.Message -match '(?i)\bpsu\b|power supply|ps failed|failure detected|malfunction|voltage|power fault|power failure' }; if($e){@($e | Select-Object TimeCreated,ProviderName,Id,LevelDisplayName,@{N='Message';E={($_.Message -replace '\r?\n',' ')}}) | ConvertTo-Json -Depth 4}else{'No PSU/power-failure-like warning or error events found in the last 30 days.'}
```

# 출력 결과
```text
No PSU/power-failure-like warning or error events found in the last 30 days.
```

# 설명
- 전원 손실, unexpected shutdown, ACPI 전원 관련 오류를 대상으로 합니다.
- 전원 이슈는 커널/부팅 로그와 함께 해석하면 더 정확합니다.

# 임계치
- `max_power_event_count`: `0`
- `failure_keywords`: 없음

# 판단기준
- **정상**: 전원 관련 이벤트 수가 기준 이내입니다.
- **경고**: 전원 이상 또는 전원 관련 오류/경고 이벤트가 임계치를 초과합니다.


