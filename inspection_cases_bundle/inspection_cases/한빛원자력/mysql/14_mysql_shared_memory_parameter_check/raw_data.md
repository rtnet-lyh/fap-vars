# 영역
PARAMETER

# 세부 점검 항목
공유 메모리 파라미터 점검

# 점검 내용
MySQL 메모리 관련 파라미터를 Windows 운영 기준으로 점검합니다.

# 구분
권고

# 명령어
```powershell
$OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); mysql -NBe "SHOW VARIABLES LIKE 'innodb_buffer_pool_size'; SHOW VARIABLES LIKE 'key_buffer_size'; SHOW STATUS LIKE 'Threads_running';"
```

# 출력 결과
```text
parameter|value
shared_buffers|2147483648
work_mem|4194304
```

# 설명
- DB 메모리 파라미터는 Windows 물리 메모리와 함께 해석해야 합니다.
- 값이 과도하면 OS 메모리 압박, 너무 작으면 성능 저하 가능성이 있습니다.

# 환경별 치환 값
- `MYSQL_CLIENT_PATH`: 현재값 `mysql`
- 명령어 치환 위치: `mysql`

# 임계치
- `max_memory_parameter_ratio`: `80.0`
- `required_memory_parameters`: 제품별 핵심 메모리 파라미터`

# 판단기준
- **정상**: 메모리 파라미터가 운영 기준에 부합합니다.
- **불량**: 메모리 파라미터 조정이 필요합니다.
