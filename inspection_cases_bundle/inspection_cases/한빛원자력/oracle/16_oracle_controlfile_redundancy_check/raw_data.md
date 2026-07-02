# 영역
HA

# 세부 점검 항목
제어 파일/메타 파일 이중화

# 점검 내용
Oracle 운영 필수 메타 파일의 이중화 구성을 Windows 기준으로 점검합니다.

# 구분
권고

# 명령어
```powershell
$OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); sqlplus -S / as sysdba @control_files.sql
```

# 출력 결과
```text
control_files|C:\app\oracle\control01.ctl;D:\DBBackup\control02.ctl
```

# 설명
- 제어 파일 또는 동등한 메타 정보 파일이 단일 경로에만 존재하지 않는지 확인합니다.
- 서로 다른 드라이브나 경로에 분산되어 있어야 장애 대응 여력이 커집니다.

# 환경별 치환 값
- `ORACLE_BASE_PATH`: 현재값 `C:\app\oracle`
- 명령어 치환 위치: `C:\app\oracle`
- `ORACLE_SQLPLUS_PATH`: 현재값 `sqlplus`
- 명령어 치환 위치: `sqlplus`

# 임계치
- `min_redundant_copy_count`: `2`
- `required_distinct_paths`: `2`

# 판단기준
- **정상**: 메타 파일 이중화 구성이 확보됩니다.
- **불량**: 단일 파일 또는 단일 경로 구성입니다.
