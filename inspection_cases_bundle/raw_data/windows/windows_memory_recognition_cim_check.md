# 영역
MEMORY

# 세부 점검 항목
설치 메모리 용량 및 모듈 상태

# 점검 내용
Win32_PhysicalMemory 정보를 통해 설치된 메모리 모듈 수와 총 물리 메모리 용량을 점검합니다.

# 구분
필수

# 명령어
```powershell
$a=Get-CimInstance Win32_PhysicalMemoryArray;$m=Get-CimInstance Win32_PhysicalMemory;"ARRAY slots=$((($a|Measure-Object -Property MemoryDevices -Sum).Sum)) max={0:N2}GiB" -f ((((($a|Measure-Object -Property MaxCapacityEx -Sum).Sum)*1KB)/1GB));$m|Select-Object DeviceLocator,BankLabel,@{N=\'SizeGiB\';E={[math]::Round($_.Capacity/1GB,2)}},Manufacturer,PartNumber,SerialNumber,ConfiguredClockSpeed,Speed,SMBIOSMemoryType,FormFactor | Format-Table -AutoSize
```

# 출력 결과
```text
BankLabel     : BANK 0
DeviceLocator : Controller0-ChannelA-DIMM0
Capacity      : 8589934592
Speed         : 4800
Manufacturer  : Samsung
```

# 설명
- DIMM 개수와 총 물리 메모리 용량을 확인해 기본 자원 구성이 기준에 맞는지 봅니다.
- 용량만 보는 항목이며 사용률은 별도 점검 항목에서 확인합니다.

# 임계치
- `min_installed_memory_gib`: `8.0`
- `failure_keywords`: 없음

# 판단기준
- **정상**: 설치 메모리 총량이 최소 기준 이상입니다.
- **경고**: 설치 메모리 총량이 최소 기준보다 적습니다.


