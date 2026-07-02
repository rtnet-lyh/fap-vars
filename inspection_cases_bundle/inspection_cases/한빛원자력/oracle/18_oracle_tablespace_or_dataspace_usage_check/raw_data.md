# 영역
STORAGE

# 세부 점검 항목
테이블스페이스/데이터영역 사용률

# 점검 내용
Oracle 데이터 저장 영역 사용률을 Windows 운영 기준에서 점검합니다.

# 구분
필수

# 명령어
```powershell
$OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); sqlplus -S / as sysdba @tablespace_usage.sql
```

# 출력 결과
```text
USERS|78.50|10240|8038
```

# 설명
- 테이블스페이스, 데이터파일, 스키마 사용량 등 제품별 저장 구조를 점검합니다.
- 공간 사용률이 높으면 확장 또는 정리 계획이 필요합니다.

# 환경별 치환 값
- `ORACLE_BASE_PATH`: 현재값 `C:\app\oracle`
- 명령어 치환 위치: `C:\app\oracle`
- `ORACLE_SQLPLUS_PATH`: 현재값 `sqlplus`
- 명령어 치환 위치: `sqlplus`

# 임계치
- `max_space_usage_percent`: `90.0`
- `min_free_space_percent`: `10.0`

# 판단기준
- **정상**: 저장 영역 사용률이 허용 범위 내입니다.
- **불량**: 저장 영역 사용률이 높습니다.
