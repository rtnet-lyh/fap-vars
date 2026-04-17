# 영역
LOG

# 세부 점검 항목
CPU 하드웨어/ECC 이벤트 로그

# 점검 내용
CPU, WHEA, ECC, Machine Check와 관련된 최근 이벤트를 검색해 하드웨어 이상 징후를 확인합니다.

# 구분
필수

# 명령어
```powershell
$e=Get-WinEvent -FilterHashtable @{LogName='System';StartTime=(Get-Date).AddDays(-30);Level=@(1,2,3)} -ErrorAction SilentlyContinue | Where-Object { $_.ProviderName -in @('Microsoft-Windows-WHEA-Logger','Microsoft-Windows-Kernel-Processor-Power') -or $_.Message -match '(?i)\\bECC\\b|uncorrectable|processor|cpu|offline' }; if($e){$e | Select-Object TimeCreated,ProviderName,Id,LevelDisplayName,@{N='Message';E={($_.Message -replace '\\r?\\n',' ')}} | Format-Table -Wrap -Auto}else{'No CPU/ECC/offline-like events found in the last 30 days.'}
```

# 출력 결과
```text
TimeCreated           ProviderName  Id   Level    Message
2026-04-10 오전 10:21:00  WHEA-Logger   19   Warning  A corrected hardware error has occurred.
```

# 설명
- CPU 자체 오류뿐 아니라 WHEA 기반 하드웨어 교정 오류까지 포함해 확인합니다.
- 이벤트가 없거나 허용 범위 이내면 정상으로 봅니다.

# 임계치
- `max_cpu_ecc_event_count`: `0`
- `failure_keywords`: 없음

# 판단기준
- **정상**: CPU/ECC 관련 오류 또는 경고 이벤트 수가 기준 이내입니다.
- **경고**: CPU, WHEA, ECC 관련 이벤트 수가 임계치를 초과합니다.


