# 영역
로그

# 세부 점검항목
커넥션풀 누수 발생 여부 점검

# 점검 내용
JDBC Connection Leak 발생여부 점검(문제 AP소스를 찾아 근본적인 원인 해결을 위해 Resourcenotclosed, Waittime outexception 등의 메모리 누수 로그 확인, DBConnectionPool 자원의 원활한 이용을 위한 사전 점검)

# 구분
필수

# 명령어 - admin_log_path: /home/exTMS/tmax/jeus/log/adminServer
```bash
grep -i "connection leak" {{ admin_log_path }}/jdbc.log
```

# 출력 결과
```text

```

# 설명
- Connection Leak 메시지: 커넥션 누수가 발생한 상황에 대한 설명을 제공함. 예를 들어, "Connection was not closed for over 300 seconds"라는 메시지는 커넥션이 일정 시간 이상 반환되지 않았음을 나타냄. 

# 임계치


# 판단기준
- **양호**: 로그에 'connection leak' 발생하지 않은 상태
- **경고**: 로그에 'connection leak' 발생한 상태
- **확인 필요**: 출력 및 해당 로그 파일(jdbc.log)이 없거나 실행불가(권한/미설치 등)로 점검 불가한 상태