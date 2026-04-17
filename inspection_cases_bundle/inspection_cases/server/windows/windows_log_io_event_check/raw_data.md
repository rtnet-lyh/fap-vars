# 영역
LOG

# 세부 점검 항목
디스크 I/O 이벤트 로그

# 점검 내용
디스크, 파일시스템, I/O 오류와 관련된 최근 이벤트를 검색합니다.

# 구분
필수

# 명령어
```powershell
$e=Get-WinEvent -FilterHashtable @{LogName='System';StartTime=(Get-Date).AddDays(-30);Level=@(1,2,3)} -ErrorAction SilentlyContinue | Where-Object { $_.ProviderName -match 'disk|storport|stornvme|nvme|ntfs|partmgr|iaStor|storahci|mpio' -or $_.Message -match '(?i)i/o error|timeout|timed out|transport failed|media error|reset to device|bad block|fc packet|dropped request|corrupt' }; if($e){$e | Select-Object TimeCreated,ProviderName,Id,LevelDisplayName,@{N='Message';E={($_.Message -replace '\\r?\\n',' ')}} | Format-Table -Wrap -Auto}else{'No I/O timeout/transport/media-like warning or error events found in the last 30 days.'}
```

# 출력 결과
```text
TimeCreated           ProviderName  Id   Level   Message
2026-04-10 오전 11:42:00  disk          153  Error   The IO operation at logical block address ...
```

# 설명
- 디스크 오류, 파일시스템 손상, I/O timeout 성격의 이벤트를 수집합니다.
- 저장장치 장애 조기 징후를 로그 기반으로 확인하는 항목입니다.

# 임계치
- `max_io_event_count`: `0`
- `failure_keywords`: 없음

# 판단기준
- **정상**: 디스크/I/O 관련 이벤트 수가 허용 범위 이내입니다.
- **경고**: 디스크 오류, 파일시스템 오류, I/O timeout 이벤트가 임계치를 초과합니다.


