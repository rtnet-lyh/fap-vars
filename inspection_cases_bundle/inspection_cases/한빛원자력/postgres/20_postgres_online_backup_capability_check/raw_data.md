# 영역
BACKUP

# 세부 점검 항목
온라인 백업 가능 여부

# 점검 내용
PostgreSQL 온라인 백업 또는 시점 복구 가능 설정을 Windows 기준으로 점검합니다.

# 구분
권고

# 명령어
```powershell
$OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); psql -Atqc "SHOW archive_mode; SHOW wal_level;" postgres
```

# 출력 결과
```text
archive_mode|on
wal_level|replica
```

# 설명
- 아카이브 모드, 바이너리 로그, WAL 레벨 등은 온라인 백업 가능 여부를 좌우합니다.
- 설정이 꺼져 있으면 무중단 백업 및 시점 복구에 제약이 생길 수 있습니다.

# 환경별 치환 값
- `POSTGRES_CLIENT_PATH`: 현재값 `psql`
- 명령어 치환 위치: `psql`

# 임계치
- `required_backup_mode`: `enabled`

# 판단기준
- **정상**: 온라인 백업 필수 설정이 활성화되어 있습니다.
- **불량**: 온라인 백업 관련 설정이 비활성화되어 있습니다.
