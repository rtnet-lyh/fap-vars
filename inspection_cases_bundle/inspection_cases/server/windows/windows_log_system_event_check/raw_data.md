# 영역
LOG

# 세부 점검 항목
시스템 주요 이벤트 로그

# 점검 내용
System, Application, Security 로그에서 주요 오류/경고 메시지를 폭넓게 검색합니다.

# 구분
필수

# 명령어
```powershell
$OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); Get-WinEvent -FilterHashtable @{LogName=@('System','Application','Security'); StartTime=(Get-Date).AddDays(-7); Level=@(1,2,3)} -ErrorAction SilentlyContinue | Where-Object { $_.Message -match '(?i)kernel|hardware|machine check|disk|filesystem|i/o|corrupt|memory|out of memory|driver|module|network|timeout|connection|service|daemon|security|unauthorized|access denied|failed' } | Select-Object -First 300 TimeCreated,LogName,ProviderName,Id,LevelDisplayName,@{N='Message';E={($_.Message -replace '\r?\n',' ')}} | ConvertTo-Json -Depth 4
```

# 출력 결과
```json
[]
```

# 설명
- kernel, hardware, disk, memory, driver, service, security, access denied 등 광범위한 키워드를 검색합니다.
- Critical/Error 수와 Warning 수를 분리해 판단합니다.

# 임계치
- `max_critical_error_count`: `0`
- `max_warning_count`: `10`
- `failure_keywords`: 없음

# 판단기준
- **정상**: Critical/Error와 Warning 이벤트 수가 모두 허용 범위 이내입니다.
- **경고**: 주요 오류 또는 경고 이벤트 수가 임계치를 초과합니다.


