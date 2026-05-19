# 영역
Connection Pool 상태

# 세부 점검항목
DB연결 객체저장공간 설정값 초과 여부 점검

# 점검 내용
DB에 연결된 객체 저장공간인 DB Connection Pool 확인(기 설정된 Max 값과 현재 사용량을 체크하여 임계치 조정 등의 활동을 위한 점검)

# 구분
필수

# 명령어 jeus_log_path: /home/exTMS/tmax/jeus/log
```bash
grep -i "connection pool exhausted" {{ jeus_log_path }}/jdbc.log
```

# 출력 결과
```text
2024-09-12 10:15:23,123 ERROR [JDBC] Connection pool exhausted for datasource 'myPool'. Maximum connections reached (30).
2024-09-12 10:17:45,456 ERROR [JDBC] Connection pool exhausted for datasource 'myPool'. Maximum connections reached (30).
```

# 설명
- Error Message: "Connection pool exhausted" 메시지가 자주 발생하면, Max Connections 설정이 부족할 수 있으며, 이 값을 늘리거나 연결 관리 방식을 최적화하는 것이 필요. 
※ 기 설정된 환경 값과 현재 사용량은 명령어를 통해서 알 수 없음.

# 임계치
max_message_count: 최대 "Connection pool exhausted" 메시지 개수


# 판단기준
- **양호**: "Connection pool exhausted" 메시지 개수가 `max_message_count`를 넘지 않은 상태
- **경고**: "Connection pool exhausted" 메시지 개수가 `max_message_count`를 넘지 않은 상태(Max Connections 설정 확인 필요)
- **확인 필요**: 출력 및 jdbc.log 파일이 없거나 실행불가(권한/미설치 등)로 점검 불가한 상태