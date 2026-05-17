# 영역
서비스 처리상태

# 세부 점검항목
평균처리시간 점검

# 점검 내용
요청건수 및 전체 처리시간, 평균처리시간 확인(평균 처리 응답시간을 확인 하여 서비스 지연 처리 확인을 위한 점검)

# 구분
권고

# 명령어
```bash
jeusadmin -u jeus -p jeus "show-thread-pool-status adminServer"
```

# 출력 결과(정상 출력)
```text
Thread Pool Name: default
Active Threads: 15
Idle Threads: 5
Max Threads: 20
Queue Size: 10
Completed Tasks: 1000
Task Count: 1015
Largest Pool Size: 18
```

# 출력 결과(접속 불가 출력)
```text
[exTMS@tips_was1:/home/exTMS]$ jeusadmin -u jeus -p jeus "show-thread-pool-status adminServer"
Attempting to connect to 127.0.0.1:9736.
The connection failed: fail to connect to 127.0.0.1:9736(/JeusMBeanServer), the node is not ready.
```

# 설명
- Active Threads: 현재 스레드 풀에서 요청을 처리 중인 스레드 수로, Active Threads가 Max Threads에 가까워지면 시스템이 과부하 상태로 성능 저하가 발생할 수 있음. 스레드 풀이 과도하게 활성화될 경우 스레드 풀 크기를 조정하거나 성능 최적화를 수행하는 것이 필요. 
- Idle Threads: 대기 중인 스레드 수로, 요청을 처리할 수 있는 여유 스레드의 수를 나타냄. Idle  Threads가 적으면 새로운 요청이 대기 상태에 들어가면서 처리 지연이 발생할 수 있으므로, 대기 스레드가 충분한지 확인하고 부족할 경우 스레드 풀 크기를 늘리거나 성능 최적화를 통해 대기 스레드를 확보하는 것이 필요. 
- Task Count: 현재 스레드 풀에서 처리 중인 전체 작업 수로, Task Count가 지나치게 높으면 
서비스의 처리 성능이 저하될 수 있음. 스레드 풀에서 처리할 수 있는 작업 수가 한계를 
넘어서면 시스템 성능에 영향을 미치므로, 처리 중인 작업 수가 많을 경우 성능 최적화 또는 스레드 풀 크기 확장이 필요. 
※ 이 정보를 통해 성능 저하나 서비스 지연 가능성을 간접적으로 파악할 수 있지만, JEUS에서 요청 처리 시간과 평균 처리 시간을 직접적으로 제공하는 명령어는 없음.

# 임계치
max_active_threads: 최대 요청 처리 스레드 수 
max_idle_thread: 최대 대기 스레드 수
max_task_count: 최대 처리 작업 수

# 판단기준 - 수동 확인 필요
- **양호**: Active Threads, Max Threads, Task Count값이 임계치(`max_active_threads`, `max_idle_thread`, `max_task_count`) 를 초과하지 않는 상태
- **경고**: Active Threads, Max Threads, Task Count값이 임계치(`max_active_threads`, `max_idle_thread`, `max_task_count`)를 초과하는 상태
- **확인 필요**: 출력이 없거나 jeusadmin 명령어 실행불가(권한/미설치/미기동 등)로 점검 불가한 상태