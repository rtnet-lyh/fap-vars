# 영역
DISK

# 세부 점검 항목
디스크 및 파티션 인식 상태

# 점검 내용
Get-Disk와 Get-Partition 결과를 이용해 디스크 수와 파티션 수가 최소 기준을 만족하는지 확인합니다.

# 구분
필수

# 명령어
```powershell
$OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); $d=Get-Disk -ErrorAction SilentlyContinue; @(@($d|ForEach-Object{[pscustomobject]@{NAME="Disk$($_.Number)";RM=[int]($_.BusType -in @('USB','SD','MMC')); 'SIZE(GB)'=[math]::Round($_.Size/1GB,2);RO=[int]$_.IsReadOnly;TYPE='disk';MOUNTPOINT='';STATUS=(@($_.OperationalStatus)-join ',')}}) + @((Get-Partition -ErrorAction SilentlyContinue)|ForEach-Object{$n=$_.DiskNumber; $dk=$d|Where-Object Number -eq $n; [pscustomobject]@{NAME="Disk$($_.DiskNumber)-Part$($_.PartitionNumber)";RM=[int]($dk.BusType -in @('USB','SD','MMC')); 'SIZE(GB)'=[math]::Round($_.Size/1GB,2);RO=[int]$_.IsReadOnly;TYPE='part';MOUNTPOINT=(($_.AccessPaths|Where-Object{$_})-join ',').TrimEnd('\');STATUS=(@($dk.OperationalStatus)-join ',')}}) + @((Get-CimInstance Win32_CDROMDrive -ErrorAction SilentlyContinue)|ForEach-Object{[pscustomobject]@{NAME=$(if($_.Drive){$_.Drive}else{$_.Caption});RM=1;'SIZE(GB)'=$(if($_.Size){[math]::Round([double]$_.Size/1GB,2)}else{$null});RO=1;TYPE='rom';MOUNTPOINT=$_.Drive;STATUS=$(if($_.MediaLoaded){$_.Status}else{'No Media'})}})) | ConvertTo-Json -Depth 3
```

# 출력 결과
```json
[
  {
    "NAME": "Disk0",
    "RM": 0,
    "SIZE(GB)": 476.94,
    "RO": 0,
    "TYPE": "disk",
    "MOUNTPOINT": "",
    "STATUS": "Online"
  },
  {
    "NAME": "Disk0-Part1",
    "RM": 0,
    "SIZE(GB)": 476.34,
    "RO": 0,
    "TYPE": "part",
    "MOUNTPOINT": "C:",
    "STATUS": "Online"
  }
]
```

# 설명
- 스토리지 장치가 OS에 인식되는지와 실제 파티션이 구성되어 있는지를 함께 점검합니다.
- 최소 디스크 수와 최소 파티션 수를 기준으로 기본 스토리지 구성을 검증합니다.

# 임계치
- `min_disk_count`: `1`
- `min_partition_count`: `1`
- `failure_keywords`: 없음

# 판단기준
- **정상**: 디스크 수와 파티션 수가 모두 최소 기준 이상입니다.
- **경고**: 디스크 미인식, 파티션 누락 등으로 기준 미달입니다.


