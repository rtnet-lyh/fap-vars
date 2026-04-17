# 영역
LOG

# 세부 점검 항목
커널/부팅 이상 이벤트 로그

# 점검 내용
커널, 버그체크, 블루스크린, 비정상 재부팅과 관련된 최근 이벤트를 검색합니다.

# 구분
필수

# 명령어
```powershell
$e=Get-WinEvent -FilterHashtable @{LogName=@('System','Application'); StartTime=(Get-Date).AddDays(-30)} -ErrorAction SilentlyContinue | Where-Object { $_.ProviderName -match 'BugCheck|Microsoft-Windows-WER-SystemErrorReporting|Microsoft-Windows-Kernel-Power' -or $_.Message -match '(?i)bugcheck|bluescreen|livekernelevent|kernel panic|panicking' -or ($_.Id -eq 41 -and $_.ProviderName -eq 'Microsoft-Windows-Kernel-Power') } | Select-Object TimeCreated,LogName,ProviderName,Id,LevelDisplayName,@{N='Message';E={($_.Message -replace '\\r?\\n',' ')}}; if($e){$e | Format-Table -Wrap -Auto}else{'No panic-like kernel events found in the last 30 days.'}
```

# 출력 결과
```text
TimeCreated           ProviderName               Id   Level   Message
2026-04-10 오전 07:11:20  Microsoft-Windows-Kernel-Power  41  Critical  The system has rebooted without cleanly shutting down first.
```

# 설명
- Kernel-Power, bugcheck, crash, panic 유사 이벤트를 중심으로 확인합니다.
- 비정상 종료나 커널 레벨 장애 징후를 빠르게 식별하기 위한 항목입니다.

# 임계치
- `max_panic_like_event_count`: `0`
- `failure_keywords`: 없음

# 판단기준
- **정상**: 커널/부팅 이상 이벤트 수가 허용 범위 이내입니다.
- **경고**: bugcheck, kernel power, panic 유사 이벤트가 임계치를 초과합니다.


