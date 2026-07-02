# 영역
LOG

# 세부 점검 항목
Dump/Trace 파일 생성 여부

# 점검 내용
PostgreSQL 장애 분석용 dump/trace 파일 생성 여부를 Windows 경로 기준으로 점검합니다.

# 구분
권고

# 명령어
```powershell
$OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); Get-ChildItem -Path 'C:\Program Files\PostgreSQL\16\data\log\*.csv' -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 20 Name, Length, LastWriteTime
```

# 출력 결과
```text
Name           Length LastWriteTime
postgres_4120.trc   20480  2026-06-29 10:12:00
```

# 설명
- 최근 생성된 trace/dump 파일은 비정상 종료나 내부 오류의 흔적일 수 있습니다.
- 파일 개수, 생성 시각, 크기를 함께 봐야 분석 우선순위를 정하기 쉽습니다.

# 환경별 치환 값
- 덤프/트레이스 경로: 현재값 `C:\Program Files\PostgreSQL\16\data\log\*.csv`
- 명령어 치환 위치: `C:\Program Files\PostgreSQL\16\data\log\*.csv`

# 임계치
- `max_recent_dump_count`: `0`
- `recent_window_hours`: `24`

# 판단기준
- **정상**: 최근 생성된 dump/trace 파일이 없습니다.
- **불량**: 최근 생성 파일이 있어 원인 분석이 필요합니다.
