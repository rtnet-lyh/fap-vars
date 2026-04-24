# 영역
MEMORY

# 세부 점검 항목
PageFile 기반 스왑 사용률

# 점검 내용
Win32_PageFileUsage를 조회해 PageFile 총량, 현재 사용량, 최대 사용률을 점검합니다.

# 구분
권고

# 명령어
```powershell
$OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); Get-CimInstance Win32_PageFileUsage | Select-Object @{N='Filename';E={$_.Name}},@{N='Type';E={'file'}},@{N='Size(MB)';E={$_.AllocatedBaseSize}},@{N='Used(MB)';E={$_.CurrentUsage}},@{N='Usage(%)';E={if($_.AllocatedBaseSize){[math]::Round(($_.CurrentUsage/$_.AllocatedBaseSize)*100,2)}else{0}}},@{N='Peak(MB)';E={$_.PeakUsage}}
```

# 출력 결과
```text
Name               AllocatedBaseSize  CurrentUsage  PeakUsage
C:\pagefile.sys  2048               128           256
```

# 설명
- 메모리 전체가 아닌 PageFile 사용량만 별도로 추적하는 항목입니다.
- 스왑 사용량이 높으면 메모리 압박 또는 튜닝 이슈 가능성을 의심할 수 있습니다.

# 임계치
- `max_swap_usage_percent`: `50.0`
- `failure_keywords`: 없음

# 판단기준
- **정상**: PageFile 사용률이 임계치 이하입니다.
- **경고**: PageFile 사용률이 임계치를 초과합니다.


