# 영역
HA

# 세부 점검 항목
변경 로그 이중화 구성

# 점검 내용
Oracle redo log group/member 구성과 경로 분산 여부를 Windows 기준으로 점검합니다.

# 구분
필수

# 명령어
```powershell
$OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); @'
SET HEADING OFF FEEDBACK OFF VERIFY OFF PAGESIZE 0
SELECT group# || '|' || member FROM v$logfile ORDER BY group#, member;
EXIT;
'@ | sqlplus -S / as sysdba
```

# 출력 결과
```text
1|D:\ORADATA\HBORA\REDO01.LOG
2|D:\ORAARCH\REDO02.LOG
3|D:\ORAARCH\REDO03.LOG
```

# 설명
- 복구 핵심 로그가 한 경로에만 몰려 있으면 단일 장애점이 됩니다.
- redo log group/member 배치와 경로 분산 여부를 함께 확인합니다.

# 환경별 치환 값
- `ORACLE_SQLPLUS_PATH`: 현재값 `sqlplus`
- 명령어 치환 위치: `sqlplus`

# 임계치
- `min_log_group_count`: `2`
- `required_log_path_diversity`: `2`

# 판단기준
- **정상**: 변경 로그 구성과 경로 분산이 적절합니다.
- **불량**: 로그 이중화 또는 경로 분산이 부족합니다.
