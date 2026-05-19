# 영역
Connection Pool 상태

# 세부 점검항목
DB연결 상태 점검

# 점검 내용
DB에 연결된 객체 저장공간인 DB Connection Pool 확인(각 컨테이너별 Enable상태 확인)

# 구분
필수

# 명령어 jeus_log_path: /home/exTMS/tmax/jeus/log
```bash
grep -i "Connection" {{ jeus_log_path }}/jdbc.log
```

# 출력 결과
```text
2024-09-12 10:00:23,123 ERROR [JDBC] Connection timeout: Unable to get a connection from the poolager 3000ms.
2024-09-12 10:05:12,789 WARN [JDBC] Connection closed by database due to inactivity.
2024-09-12 10:22:45,456 INFO [JDBC] Connection established to database.
```

# 설명
- Connection Timeout: 커넥션 풀에서 설정된 시간 안에 DB 연결을 가져오지 못하면 Connection Timeout 오류가 발생하므로, 커넥션 풀 크기를 늘리거나 데이터베이스 성능을 최적화해 문제를 해결하는 것이 필요. 
- Connection Closed by Database: 비활성 연결이 자주 끊어지는 경우, 데이터베이스나 커넥션 풀 설정에서 idle timeout을 적절히 조정해 비활성 시간을 줄이는 것이 권고.
- Connection Established: 데이터베이스에 성공적으로 연결된 경우 추가적인 조치가 필요하지 않으나, 연결 시간이 과도하게 길어지면 데이터베이스 성능을 점검 필요.
※ 로그 파일을 통해서 DB 커넥션 풀에 대한 로그를 확인함으로써 DB연결 상태를 점검할 수 있으며, 각 컨테이너별 Enable 상태를 명령어로 직접 확인하는 것은 불가능함.

# 임계치

# 판단기준 - 수동 확인 필요
- **양호**: Connection Timeout 에러, Connection closed by database 경고, Connection established to database 메시지에 이상이 없는 상태
- **경고**: Connection Timeout 에러, Connection closed by database 경고, Connection established to database 메시지에 이상이 있는 상태
- **확인 필요**: 출력 및 jdbc.log 파일이 없거나 실행불가(권한/미설치 등)로 점검 불가한 상태