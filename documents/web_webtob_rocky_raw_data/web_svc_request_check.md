# 영역
서비스

# 세부 점검항목
사용자 요청량 처리 수 점검

# 점검 내용
WEB 서비스 지연 시 상태 확인을 위해 WEB 환경 설정값과 사용자 요청건수가 적절하게 설정되었는지 확인

# 구분
권고

# 명령어
```bash
webtob_ctl status
```

# 출력 결과
```text
Status: RUNNING
MaxConnections: 1000
MaxRequestPerConnection: 50
MaxWorkerThreads: 200
```

# 설명
- MaxConnections: 동시에 처리 가능한 최대 연결 수를 설정하며, 설정값이 서버의 처리 용량에 적합한지 확인하고 조정하는 것이 권고. 
- MaxRequestPerConnection: 하나의 연결에서 처리할 수 있는 최대 요청 수를 설정하며, 요청 패턴에 맞추어 적절한 값 설정 필요. 
- MaxWorkerThreads: 요청을 처리할 수 있는 최대 워커 스레드 수를 설정하며, 서버 성능에 맞는 적절한 수치 설정 권고.


# 임계치
max_connections: 동시 처리 가능한 최대 연결 수
max_request_per_connection: 하나의 연결에서 처리할 수 있는 최대 요청 수
max_worker_threads: 요청을 처리할 수 있는 최대 워커 스레드 수

# 판단기준
- **양호**: `max_connections`, `max_request_per_connection`, `max_worker_threads`가 적절한 수치인 상태
- **경고**: `max_connections`, `max_request_per_connection`, `max_worker_threads`가 적절하지 않은 상태
- **확인 필요**: webtob_ctl 명령이 없거나 실행불가(권한/미설치 등)로 점검 불가한 상태
