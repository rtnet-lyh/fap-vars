# 영역
CPU

# 세부 점검 항목
CPU 소켓, 코어, 논리 프로세서 수

# 점검 내용
Win32_Processor 정보를 이용해 CPU 소켓 수, 총 코어 수, 총 논리 프로세서 수를 점검합니다.

# 구분
필수

# 명령어
```powershell
$OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); Get-CimInstance Win32_Processor | Select-Object Name,SocketDesignation,Manufacturer,MaxClockSpeed,NumberOfCores,NumberOfLogicalProcessors | Format-List
```

# 출력 결과
```text
Name                      : Intel(R) Core(TM) i7-1360P
SocketDesignation         : U3E1
Manufacturer              : GenuineIntel
MaxClockSpeed             : 2200
NumberOfCores             : 12
NumberOfLogicalProcessors : 16
```

# 설명
- 장착된 프로세서별 코어 수와 논리 프로세서 수를 합산합니다.
- 최소 소켓 수, 최소 총 코어 수, 최소 총 논리 프로세서 수를 동시에 확인합니다.

# 임계치
- `min_socket_count`: `1`
- `min_total_core_count`: `4`
- `min_total_logical_processor_count`: `8`
- `failure_keywords`: 없음

# 판단기준
- **정상**: 소켓 수, 코어 수, 논리 프로세서 수가 모두 임계치 이상입니다.
- **경고**: 필수 수량 중 하나라도 임계치보다 적습니다.


