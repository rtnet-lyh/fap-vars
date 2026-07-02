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
$OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); @'
SET HEADING OFF FEEDBACK OFF VERIFY OFF PAGESIZE 0
SELECT tablespace_name || '|' ||
       ROUND((used_space * t.block_size) / 1024 / 1024, 2) || '|' ||
       ROUND((tablespace_size * t.block_size) / 1024 / 1024, 2) || '|' ||
       ROUND(used_percent, 2)
FROM dba_tablespace_usage_metrics m
JOIN dba_tablespaces t ON m.tablespace_name = t.tablespace_name;
EXIT;
'@ | sqlplus -S / as sysdba
```

# 출력 결과
```text
USERS|8038|10240|78.50
```

# 설명
- 테이블스페이스와 데이터파일 사용률을 함께 보면 확장 필요 시점을 판단하기 쉽습니다.
- 공간 사용률이 높으면 증설 또는 데이터 정리 계획이 필요합니다.

# 환경별 치환 값
- `ORACLE_SQLPLUS_PATH`: 현재값 `sqlplus`
- 명령어 치환 위치: `sqlplus`

# 임계치
- `max_space_usage_percent`: `90.0`
- `min_free_space_percent`: `10.0`

# 판단기준
- **정상**: 저장 영역 사용률이 허용 범위 내입니다.
- **불량**: 저장 영역 사용률이 높습니다.
