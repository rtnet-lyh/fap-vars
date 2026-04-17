# 영역
LOG

# 세부 점검 항목
팬 및 냉각 관련 이벤트 로그

# 점검 내용
팬, 쿨링, 열 경보와 관련된 이벤트 로그를 검색해 냉각 계통 이상 여부를 확인합니다.

# 구분
필수

# 명령어
```powershell
$f=Get-CimInstance Win32_Fan -ErrorAction SilentlyContinue; $e=Get-WinEvent -FilterHashtable @{LogName='System';StartTime=(Get-Date).AddDays(-30);Level=@(1,2,3)} -ErrorAction SilentlyContinue | Where-Object { $_.Message -match '(?i)\\bfan\\b|fan fail|cooling|thermal|overheat|fan speed too low|failure detected' }; if($f){$f | Select-Object Name,Status,DesiredSpeed,VariableSpeed,Availability,ConfigManagerErrorCode | Format-Table -Auto} else {'No Win32_Fan data exposed by firmware/driver.'}; if($e){$e | Select-Object -First 50 TimeCreated,ProviderName,Id,LevelDisplayName,@{N='Message';E={($_.Message -replace '\\r?\\n',' ')}} | Format-Table -Wrap -Auto} else {'No fan-related warning/error events found in the last 30 days.'}
```

# 출력 결과
```text
No fan or thermal warning/error events found in the last 30 days.
```

# 설명
- 센서 경고, 냉각 장치 이상, 과열 관련 메시지를 검색합니다.
- 하드웨어 이벤트가 없는 경우 정상으로 해석합니다.

# 임계치
- `max_fan_event_count`: `0`
- `failure_keywords`: 없음

# 판단기준
- **정상**: 팬/냉각 관련 이벤트가 없거나 허용 범위 이내입니다.
- **경고**: 팬 고장, 냉각 장애, 과열 경고 이벤트가 임계치를 초과합니다.


