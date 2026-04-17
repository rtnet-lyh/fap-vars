# 영역
DISK

# 세부 점검항목
Disk 이중화 정상 여부

# 점검 내용
Windows Storage 모듈 기준 물리/가상 디스크 이중화 상태 확인

# 구분
필수

# 명령어
```powershell
$ErrorActionPreference = 'Stop'; $physical = @(); $virtual = @(); $storageModuleAvailable = $false; if (Get-Command Get-PhysicalDisk -ErrorAction SilentlyContinue) { $storageModuleAvailable = $true; $physical = @(Get-PhysicalDisk | Select-Object FriendlyName, HealthStatus, OperationalStatus, MediaType, Size) }; if (Get-Command Get-VirtualDisk -ErrorAction SilentlyContinue) { $storageModuleAvailable = $true; $virtual = @(Get-VirtualDisk | Select-Object FriendlyName, HealthStatus, OperationalStatus, ResiliencySettingName, Size) }; [pscustomobject]@{ storage_module_available = $storageModuleAvailable; physical_disks = $physical; virtual_disks = $virtual } | ConvertTo-Json -Compress -Depth 6
```

# 출력 결과
```json
{"storage_module_available":true,"physical_disks":[{"FriendlyName":"PhysicalDisk0","HealthStatus":"Healthy","OperationalStatus":"OK","MediaType":"SSD","Size":107374182400}],"virtual_disks":[]}
```

# 설명
- Get-PhysicalDisk, Get-VirtualDisk로 Storage 모듈 기준 디스크 HealthStatus를 확인한다.
- Storage 모듈을 사용할 수 없으면 벤더 도구 또는 관리 콘솔로 이중화 상태를 수동 확인한다.

# 임계치
없음

# 판단기준
- **양호**: Storage 모듈 기준 HealthStatus가 정상인 경우
- **주의**: Storage 모듈 또는 지원 장치가 없어 수동 확인이 필요한 경우
- **경고**: HealthStatus가 비정상인 디스크가 확인되는 경우
