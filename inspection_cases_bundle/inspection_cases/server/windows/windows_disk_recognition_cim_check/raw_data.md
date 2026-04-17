# 영역
DISK

# 세부 점검항목
Disk 인식 여부 점검

# 점검 내용
Windows CIM 기준 디스크 인식 및 상태 확인

# 구분
필수

# 명령어
```powershell
$ErrorActionPreference = 'Stop'; $disks = Get-CimInstance Win32_DiskDrive | Select-Object DeviceID, Model, InterfaceType, MediaType, Size, Status; $bad = @($disks | Where-Object { $_.Status -and $_.Status -ne 'OK' }); [pscustomobject]@{ disk_count = @($disks).Count; abnormal_disk_count = @($bad).Count; disks = $disks } | ConvertTo-Json -Compress -Depth 6
```

# 출력 결과
```json
{"disk_count":1,"abnormal_disk_count":0,"disks":[{"DeviceID":"\\\\.\\PHYSICALDRIVE0","Model":"Demo Disk","InterfaceType":"SCSI","MediaType":"Fixed hard disk media","Size":107374182400,"Status":"OK"}]}
```

# 설명
- Win32_DiskDrive로 Windows가 인식한 디스크 수와 상태를 확인한다.
- 디스크가 없거나 Status가 OK가 아니면 디스크, 컨트롤러, 드라이버 상태를 확인한다.

# 임계치
없음

# 판단기준
- **양호**: 디스크가 1개 이상 인식되고 비정상 상태 디스크가 없는 경우
- **경고**: 디스크가 인식되지 않거나 Status가 OK가 아닌 디스크가 있는 경우
