# 영역
RESOURCE

# 세부 점검 항목
DB 프로세스 물리 CPU 사용률

# 점검 내용
PostgreSQL 프로세스 CPU 사용량과 Windows 전체 CPU 부하를 함께 점검합니다.

# 구분
권고

# 명령어
```powershell
$OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); Get-Process -Name 'postgres' -ErrorAction SilentlyContinue | Select-Object ProcessName, Id, CPU; Get-Counter '\Processor(_Total)\% Processor Time' -SampleInterval 1 -MaxSamples 3
```

# 출력 결과
```text
ProcessName Id CPU
postgres      5024 18.2

Timestamp                  CounterSamples
2026-06-29 10:00:00       24.31
```

# 설명
- 프로세스 누적 CPU 시간과 전체 CPU 카운터를 같이 보면 부하 추세를 해석하기 쉽습니다.
- 장시간 높은 사용률이 지속되면 장기 실행 SQL이나 리소스 병목을 의심합니다.

# 환경별 치환 값
- 이 항목은 현재 raw_data.md에 보이는 경로, 서비스명, 포트, 실행 파일명만 환경에 맞게 치환

# 임계치
- `max_cpu_percent`: `80.0`
- `check_samples`: `3`

# 판단기준
- **정상**: DB 관련 CPU 사용률이 허용 범위 내입니다.
- **불량**: CPU 사용률이 높거나 고부하가 지속됩니다.
