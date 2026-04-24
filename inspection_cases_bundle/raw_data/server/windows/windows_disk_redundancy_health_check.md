# 영역
DISK

# 세부 점검 항목
Storage Spaces RAID 상태

# 점검 내용
Get-Disk, Get-VirtualDisk, Get-PhysicalDisk를 조합해 Storage Spaces RAID의 상태와 구성 건전성을 점검합니다.

# 구분
필수

# 명령어
```powershell
$OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); Get-Disk | ForEach-Object { $d=$_; $vd=Get-VirtualDisk -Disk $d -ErrorAction SilentlyContinue; if($vd){ $pd=$vd | Get-PhysicalDisk -ErrorAction SilentlyContinue; \"Disk $($d.Number) [$($d.FriendlyName)] : Storage Spaces RAID device / State=$((@($vd.OperationalStatus) | Sort-Object -Unique) -join ',') / Health=$($vd.HealthStatus) / RaidDevices=$($pd.Count) / ActiveDevices=$(($pd | Where-Object {$_.OperationalStatus -eq 'OK'} | Measure-Object).Count) / WorkingDevices=$(($pd | Where-Object {$_.HealthStatus -eq 'Healthy'} | Measure-Object).Count) / FailedDevices=$(($pd | Where-Object {$_.OperationalStatus -ne 'OK' -or $_.HealthStatus -ne 'Healthy'} | Measure-Object).Count) / SpareDevices=$(try{(($vd | Get-StoragePool | Get-PhysicalDisk | Where-Object {$_.Usage -eq 'HotSpare'} | Measure-Object).Count)}catch{0})\" } else { \"Disk $($d.Number) [$($d.FriendlyName)] : does not appear to be a Storage Spaces RAID device\" } }
```

# 출력 결과
```text
Disk 1 [DataPool] : Storage Spaces RAID device / State=OK / Health=Healthy / RaidDevices=2 / ActiveDevices=2 / WorkingDevices=2 / FailedDevices=0 / SpareDevices=0
```

# 설명
- RAID 상태, Health, 활성 디스크 수, 장애 디스크 수, 스페어 디스크 수를 함께 확인합니다.
- Storage Spaces RAID 장치를 찾지 못한 경우에도 점검 실패로 처리합니다.

# 임계치
- `require_spare_device`: `0`
- `failure_keywords`: 없음

# 판단기준
- **정상**: RAID 상태가 `OK`, Health가 `Healthy`이고 장애 디스크가 없습니다.
- **불량**: Storage Spaces RAID 장치를 찾지 못했거나, RAID 상태 저하, Health 이상, 실패 디스크 발생, 스페어 부족이 감지됩니다.


