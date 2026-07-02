# 영역
PARAMETER

# 세부 점검 항목
공유 메모리 파라미터 점검

# 점검 내용
Oracle 메모리 관련 파라미터를 Windows 운영 기준으로 점검합니다.

# 구분
권고

# 명령어
```powershell
$OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); @'
SET HEADING OFF FEEDBACK OFF VERIFY OFF PAGESIZE 0
SELECT 'sga_target|' || value FROM v$parameter WHERE name = 'sga_target';
SELECT 'pga_aggregate_target|' || value FROM v$parameter WHERE name = 'pga_aggregate_target';
SELECT 'memory_target|' || value FROM v$parameter WHERE name = 'memory_target';
EXIT;
'@ | sqlplus -S / as sysdba
```

# 출력 결과
```text
sga_target|8589934592
pga_aggregate_target|2147483648
memory_target|0
```

# 설명
- Oracle 메모리 파라미터는 Windows 물리 메모리와 함께 해석해야 합니다.
- 값이 과도하면 OS 메모리 압박, 너무 작으면 성능 저하 가능성이 있습니다.

# 환경별 치환 값
- `ORACLE_SQLPLUS_PATH`: 현재값 `sqlplus`
- 명령어 치환 위치: `sqlplus`

# 임계치
- `max_memory_parameter_ratio`: `80.0`
- `required_memory_parameters`: `sga_target,pga_aggregate_target,memory_target`

# 판단기준
- **정상**: 메모리 파라미터가 운영 기준에 부합합니다.
- **불량**: 메모리 파라미터 조정이 필요합니다.
