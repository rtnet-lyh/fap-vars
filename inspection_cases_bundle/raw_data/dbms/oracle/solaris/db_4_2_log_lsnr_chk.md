# 영역
로그 점검

# 세부 점검항목
리스너(DB 서비스 연결) 로그 파일 점검

# 점검 내용
리스너를 통해 DB에 접근하는 클라이언트에 대한 로그 파일로 세션 접속(WAS와 DB간)에 문제가 있는지 점검

# 구분
필수

# 명령어 - lsnr_log_dir 변수: /TTIPS_GRID/oracle/grid/gridbase/diag/tnslsnr/exTMStotalDB1/listener/trace
```bash
tail -200 {{ lsnr_log_dir }}/listener.log | egrep -i "connection refused|timeout|TNS listener stopped|warning|slow|delay|TNS-12514|TNS-12541|TNS-12170" {{ lsnr_log_dir }}/listener.log
```

# 출력 결과 (테스트 서버: 172.18.8.91)
```text
oratips@exTMStotalDB1:/TTIPS_HOME/oracle/dbms/diag/tnslsnr$ egrep -i "connection refused|timeout|TNS listener stopped|warning|slow|delay|TNS-12514|TNS-12541|TNS-12170" /TTIPS_GRID/oracle/grid/gridbase/diag/tnslsnr/exTMStotalDB1/listener/trace/listener.log
TNS-12514: TNS:listener does not currently know of service requested in connect descriptor
TNS-12514: TNS:listener does not currently know of service requested in connect descriptor
TNS-12514: TNS:listener does not currently know of service requested in connect descriptor
TNS-12514: TNS:listener does not currently know of service requested in connect descriptor
TNS-12514: TNS:listener does not currently know of service requested in connect descriptor
TNS-12514: TNS:listener does not currently know of service requested in connect descriptor
```

# 설명
- TNS-12514: TNS:listener does not currently know of service requested in connect descriptor: 요청된 서비스에 대한 정보가 리스너에 존재하지 않음을 나타내며, 로그에서 해당 메시지가 출력되면 서비스 설정을 확인해야 하고, 데이터베이스 서비스가 정상적으로 등록되어 있는지 점검한 후 필요 시 리스너를 재시작하는 것이 필요. 
- connection refused: 클라이언트가 리스너에 연결 요청을 했으나 연결이 거부되었음을 나타내며, 해당 메시지가 
출력된 경우 리스너가 실행 중인지 확인하고, 리스너가 정지된 경우에는 즉시 리스너를 시작해야 함. 
- timeout: 연결 시도 시간이 초과되었음을 나타내며, 이 메시지가 출력될 때는 연결 요청 후 일정 시간 내에 응답이 없었던 경우이므로 네트워크 상태를 점검하고 필요 시 리스너 및 클라이언트 설정을 조정해야 함. 
- TNS listener stopped: 리스너가 정지된 상태임을 나타내며, 이 메시지가 출력된 경우 리스너의 상태를 확인하고, 리스너가 중지된 경우 즉시 리스너를 시작해야 함. 
- warning: potential configuration issue detected: 구성 문제의 가능성을 나타내는 경고 메시지로, 해당 메시지를 통해 구성 파일을 검토해야 
하며, 구성 파일을 점검하고 필요한 수정 사항을 적용하는 것이 권고. 
- slow response from client: 클라이언트에서 느린 응답이 감지되었음을 나타내며, 이 메시지가 출력될 경우 클라이언트의 성능을 확인하고, 성능 문제를 해결하기 위해 네트워크 상태와 시스템 리소스를 점검해야 함. 
- delay: network latency detected: 네트워크 지연이 감지되었음을 나타내며, 이 메시지가 출력되면 네트워크의 응답 시간을 확인하고, 네트워크 지연 문제를 해결하기 위해 네트워크 구성 및 상태를 점검해야 함.

# 임계치

# 판단기준  - 확인 필요
- **양호**: 출력값에 결과가 나오지 않은 상태
- **경고**: 출력값에 결과가 나온 상태
- **확인 필요**: 로그 파일 및 경로가 존재하지 않는 경우
