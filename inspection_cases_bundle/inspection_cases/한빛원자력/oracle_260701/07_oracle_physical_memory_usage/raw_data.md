# 영역
RESOURCE

# 세부 점검 항목
DB 프로세스 물리 메모리 사용률

# 점검 내용
Oracle 관련 프로세스의 Windows 메모리 사용량을 점검합니다.

# 구분
권고

# 명령어
```powershell
$OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); Get-Process -Name 'oracle' -ErrorAction SilentlyContinue | Select-Object ProcessName, Id, WorkingSet64, PagedMemorySize64, VirtualMemorySize64
```

# 출력 결과
```text
ProcessName         : oracle
Id                  : 4388
WorkingSet64        : 16250589184
PagedMemorySize64   : 16340754432
VirtualMemorySize64 : 25260531712
```

# 설명
- Linux `%MEM/RSS` 대신 Windows `WorkingSet64`, `PagedMemorySize64` 값을 봅니다.
- 특정 프로세스 메모리 사용량이 급증하면 스와핑, 응답 지연, 서비스 불안정으로 이어질 수 있습니다.

# 환경별 치환 값
- 프로세스명: 현재값 `oracle`
- 명령어 치환 위치: `Get-Process -Name 'oracle'`

# 임계치
- `max_workingset_mb`: 환경 기준값 사용
- `max_memory_growth_trend`: 최근 추세 확인`

# 판단기준
- **정상**: 프로세스 메모리 사용량이 안정적입니다.
- **불량**: 메모리 사용량이 과도하거나 급증 추세가 확인됩니다.
