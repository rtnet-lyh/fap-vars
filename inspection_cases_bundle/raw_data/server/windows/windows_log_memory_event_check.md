# 영역
LOG

# 세부 점검 항목
메모리 오류 이벤트 로그

# 점검 내용
메모리 오류, WHEA 메모리, Pagefile 부족 등과 관련된 이벤트를 검색합니다.

# 구분
필수

# 명령어
```powershell
$OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); $e=Get-WinEvent -FilterHashtable @{LogName='System';StartTime=(Get-Date).AddDays(-30);Level=@(1,2,3)} -ErrorAction SilentlyContinue | Where-Object { $_.ProviderName -eq 'Microsoft-Windows-WHEA-Logger' -or $_.Message -match '(?i)\becc\b|memory error|single-bit|multi-bit|uncorrectable' }; if($e){@($e | Select-Object TimeCreated,ProviderName,Id,LevelDisplayName,@{N='Message';E={($_.Message -replace '\r?\n',' ')}}) | ConvertTo-Json -Depth 4}else{'No ECC/memory-error-like events found in the last 30 days.'}
```

# 출력 결과
```text
No ECC/memory-error-like events found in the last 30 days.
```

# 설명
- 메모리 오류, corrected memory error, out of memory 성격의 이벤트를 확인합니다.
- 실제 메모리 사용률과는 별개로 하드웨어 또는 시스템 이벤트 관점에서 점검합니다.

# 임계치
- `max_memory_error_event_count`: `0`
- `failure_keywords`: 없음

# 판단기준
- **정상**: 메모리 관련 오류/경고 이벤트 수가 기준 이내입니다.
- **경고**: 메모리 하드웨어 또는 메모리 부족 이벤트가 임계치를 초과합니다.


