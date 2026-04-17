# 영역
FILESYSTEM

# 세부 점검항목
파일시스템 사용량

# 점검 내용
Windows 고정 디스크 파일시스템 사용률 확인

# 구분
권고

# 명령어
```powershell
$ErrorActionPreference = 'Stop'; $drives = Get-CimInstance Win32_LogicalDisk -Filter "DriveType=3" | ForEach-Object { $size = [double]$_.Size; $free = [double]$_.FreeSpace; $usage = if ($size -gt 0) { [math]::Round((($size - $free) / $size) * 100, 2) } else { 0 }; [pscustomobject]@{ device_id = $_.DeviceID; volume_name = $_.VolumeName; size_bytes = [int64]$size; free_bytes = [int64]$free; usage_percent = $usage } }; [pscustomobject]@{ drive_count = @($drives).Count; drives = @($drives) } | ConvertTo-Json -Compress -Depth 6
```

# 출력 결과
```json
{"drive_count":1,"drives":[{"device_id":"C:","volume_name":"Windows","size_bytes":107374182400,"free_bytes":53687091200,"usage_percent":50.0}]}
```

# 설명
- Win32_LogicalDisk에서 고정 디스크(DriveType=3)의 용량과 여유 공간을 조회한다.
- 드라이브 사용률이 임계치를 초과하면 로그 정리, 불필요 파일 삭제, 용량 증설 검토가 필요하다.

# 임계치
max_filesystem_usage_percent: 80

# 판단기준
- **양호**: 모든 고정 드라이브 사용률이 임계치 이하인 경우
- **경고**: 하나 이상의 드라이브 사용률이 임계치를 초과한 경우
