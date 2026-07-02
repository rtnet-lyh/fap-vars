# 영역
HA

# 세부 점검 항목
Active-Standby/복제 상태

# 점검 내용
Oracle 이중화/복제 상태를 Windows 환경의 DB 클라이언트 명령으로 점검합니다.

# 구분
필수

# 명령어
```powershell
$OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); sqlplus -S / as sysdba @dataguard_status.sql
```

# 출력 결과
```text
standby01|streaming|sync|00:00:00.120|00:00:00.150
```

# 설명
- 복제 대상 상태, sync 상태, 지연 시간, 최근 오류 여부를 함께 봐야 합니다.
- 테스트 절체 전 단계에서 가장 중요하게 확인할 항목 중 하나입니다.

# 환경별 치환 값
- `ORACLE_SQLPLUS_PATH`: 현재값 `sqlplus`
- 명령어 치환 위치: `sqlplus`

# 임계치
- `required_replication_state`: `healthy/streaming/synchronized`
- `max_replication_lag_seconds`: `60`

# 판단기준
- **정상**: 복제 상태가 정상이며 지연이 허용 범위 내입니다.
- **불량**: 복제 중단 또는 지연 증가가 확인됩니다.
