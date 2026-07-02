# 영역
LOG

# 세부 점검 항목
DB 엔진 내부 로그 점검

# 점검 내용
Oracle 엔진 내부 경고/오류 로그를 Windows 로그 경로 기준으로 점검합니다.

# 구분
필수

# 명령어
```powershell
$OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); Select-String -Path 'C:\app\oracle\diag\rdbms\orcl\orcl\trace\alert_orcl.log' -Pattern 'warning|critical|alert|checksum|integrity|space|disk|panic|fatal' -CaseSensitive:$false | Select-Object -First 20
```

# 출력 결과
```text
C:\app\oracle\diag\rdbms\orcl\orcl\trace\engine.log:212: WARNING checksum mismatch detected
```

# 설명
- 심각한 오류 전 단계의 경고성 메시지도 장기적으로는 장애 전조일 수 있습니다.
- 특히 checksum, integrity, disk, panic, fatal 계열 키워드를 중점 확인합니다.

# 환경별 치환 값
- `ORACLE_TRACE_PATH`: 현재값 `C:\app\oracle\diag\rdbms\orcl\orcl\trace`
- 명령어 치환 위치: `C:\app\oracle\diag\rdbms\orcl\orcl\trace\alert_orcl.log`

# 임계치
- `max_critical_event_count`: `0`
- `failure_keywords`: `critical,checksum,integrity,panic,fatal`

# 판단기준
- **정상**: 내부 엔진 경고/오류 흔적이 없습니다.
- **불량**: 내부 엔진 이상 징후가 확인됩니다.
