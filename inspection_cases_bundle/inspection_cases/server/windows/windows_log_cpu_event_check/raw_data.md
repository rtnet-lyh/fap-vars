# 영역
로그

# 세부 점검항목
CPU 로그

# 점검 내용
최근 24시간 System 이벤트에서 CPU 관련 오류/경고 확인

# 구분
필수

# 명령어
```powershell
$ErrorActionPreference = 'Stop'; $since = (Get-Date).AddHours(-24); $events = @(Get-WinEvent -FilterHashtable @{LogName='System'; Level=1,2,3; StartTime=$since} -ErrorAction SilentlyContinue | Where-Object { ($_.ProviderName + ' ' + $_.Message) -match 'processor|cpu|thermal|machine check' } | Select-Object -First 20 TimeCreated, Id, LevelDisplayName, ProviderName, Message); [pscustomobject]@{ lookback_hours = 24; keyword_pattern = 'processor|cpu|thermal|machine check'; event_count = @($events).Count; events = $events } | ConvertTo-Json -Compress -Depth 6
```

# 출력 결과
```json
{"lookback_hours":24,"keyword_pattern":"demo","event_count":0,"events":[]}
```

# 설명
- 최근 24시간 System 이벤트 로그에서 Level 1, 2, 3 이벤트를 조회하고 항목별 키워드로 필터링한다.
- 이벤트가 임계치보다 많으면 장애 징후 또는 반복 경고 여부를 확인한다.

# 임계치
max_event_count: 0

# 판단기준
- **양호**: 이벤트 로그 검출 건수가 임계치 이하인 경우
- **주의**: 관련 오류/경고 이벤트가 임계치를 초과해 추가 확인이 필요한 경우
