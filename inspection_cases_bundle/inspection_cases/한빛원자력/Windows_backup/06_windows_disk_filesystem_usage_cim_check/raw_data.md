# 영역
FILESYSTEM

# 세부 점검 항목
파일시스템 사용률

# 점검 내용
고정 디스크 볼륨의 전체 용량과 여유 공간을 바탕으로 파일시스템 사용률을 점검합니다.

# 구분
필수

# 명령어
```powershell
$OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); Get-CimInstance Win32_Volume | Where-Object { $_.DriveType -eq 3 -and $_.Capacity } | Select-Object @{N='Filesystem';E={if($_.DriveLetter){$_.DriveLetter}else{$_.Name.TrimEnd('\')}}},@{N='Size(GB)';E={[math]::Round($_.Capacity/1GB,2)}},@{N='Used(GB)';E={[math]::Round(($_.Capacity-$_.FreeSpace)/1GB,2)}},@{N='Avail(GB)';E={[math]::Round($_.FreeSpace/1GB,2)}},@{N='Use%';E={[math]::Round((($_.Capacity-$_.FreeSpace)/$_.Capacity)*100,2)}},@{N='Mounted on';E={$_.Name.TrimEnd('\')}} | ConvertTo-Json -Depth 3
```

# 출력 결과
```json
[
  {
    "Filesystem": "C:",
    "Size(GB)": 476.34,
    "Used(GB)": 181.25,
    "Avail(GB)": 295.09,
    "Use%": 38.05,
    "Mounted on": "C:"
  }
]
```

# 설명
- 드라이브별 사용률과 가용률을 계산해 공간 부족 위험을 평가합니다.
- 사용률 상한과 가용률 하한을 동시에 확인합니다.

# 임계치
- `max_usage_percent`: `80.0`
- `min_available_percent`: `20.0`
- `failure_keywords`: 없음

# 판단기준
- **정상**: 모든 드라이브의 사용률이 임계치 이하이고 여유율이 충분합니다.
- **경고**: 하나 이상의 드라이브가 사용률 상한을 넘거나 가용률 하한 아래입니다.


