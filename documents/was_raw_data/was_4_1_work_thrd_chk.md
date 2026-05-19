# 영역
Thread Pool 상태

# 세부 점검항목
어플리케이션 수행 공간 설정값 초과 여부 점검

# 점검 내용
Work Thread Pool 확인(기 설정된 Max 값과 현재 사용량을 체크하여 임계치 조정 등의 활동을 위한 점검)

# 구분
필수

# 명령어
```bash
for pid in $(ps -ef | grep "jeus.server.ServerBootstrapper" | grep -v grep | awk '{print $2}'); do echo "======== PID: $pid ========"; jstack $pid | awk '
/^"/ {thread=$0} /Thread.State/ {state=$0}
/java.util.concurrent.ThreadPoolExecutor/ {
print thread
print state
print $0
print ""
}
'; done; 
```

# 출력 결과
```text
[root@tips_was1 ~]# for pid in $(ps -ef | grep "jeus.server.ServerBootstrapper" | grep -v grep | awk '{print $2}'); do echo "======== PID: $pid ========"; jstack pid | awk '
> /^"/ {thread=$0} /Thread.State/ {state=$0}
> /java.util.concurrent.ThreadPoolExecutor/ {
> print thread
> print state
> print $0
> print ""
> }
> '; done;
======== PID: 1559740 ========
"jspEngineFileWriter-exTMS_RENEW-1.0-1" #193 daemon prio=5 os_prio=0 tid=0x00007ff7e8796800 nid=0x180ba3 waiting on condition [0x00007ff904f9c000]
   java.lang.Thread.State: WAITING (parking)
        at java.util.concurrent.ThreadPoolExecutor.getTask(ThreadPoolExecutor.java:1074)

"jspEngineFileWriter-exTMS_RENEW-1.0-1" #193 daemon prio=5 os_prio=0 tid=0x00007ff7e8796800 nid=0x180ba3 waiting on condition [0x00007ff904f9c000]
   java.lang.Thread.State: WAITING (parking)
        at java.util.concurrent.ThreadPoolExecutor.runWorker(ThreadPoolExecutor.java:1134)
        ..
======== PID: 1567015 ========
"jspEngineFileWriter-exTMS_RENEW-1.0-1" #193 daemon prio=5 os_prio=0 tid=0x00007ff7e8796800 nid=0x180ba3 waiting on condition [0x00007ff904f9c000]
   java.lang.Thread.State: WAITING (parking)
        at java.util.concurrent.ThreadPoolExecutor.getTask(ThreadPoolExecutor.java:1074)

"jspEngineFileWriter-exTMS_RENEW-1.0-1" #193 daemon prio=5 os_prio=0 tid=0x00007ff7e8796800 nid=0x180ba3 waiting on condition [0x00007ff904f9c000]
   java.lang.Thread.State: WAITING (parking)
        at java.util.concurrent.ThreadPoolExecutor.runWorker(ThreadPoolExecutor.java:1134)
         ..
```

# 설명
- Thread State (WAITING, RUNNABLE): 스레드의 현재 상태로. 예를 들어, WAITING 상태는 스레드가 작업을 기다리고 있음을 의미하고, RUNNABLE은 실행 중인 상태를 나타냄. 스레드가 WAITING 상태에서 너무 오래 대기하고 있을 경우, 시스템 자원이 부족하거나 스레드 풀이 과부하 상태일 수 있으므로 리소스를 추가하거나 스레드 풀 설정을 최적화하는 것이 필요. 
- 스레드 풀의 설정값(예: 최대 스레드 수)을 초과한 상태라면, 스레드가 대기하거나 차단되는 빈도가 늘어날 수 있고, WAITING 상태의 스레드가 오랫동안 지속되거나, BLOCKED 상태의 스레드가 많아지면 스레드 풀 과부하 상태일 가능성이 크므로, 이 상태를 통해 스레드 풀의 크기를 조정하거나, 작업 부하를 줄일 필요가 있음을 판단할 수 있음. 
※ 명령어로만 애플리케이션 수행 공간 설정값(예: Work Thread Pool의 크기 등)의 초과 여부를 직접적으로 확인하는 것은 어려움. 

# 임계치
max_thread_pool: 기 설정된 최대 스레드 풀의 설정값


# 판단기준
- **양호**: 출력된 스레드명의 개수가 `max_thread_pool`를 초과하지 않고 WAITING/BLOCKED 상태의 스레드가 적은 상태
- **경고**: 출력된 스레드명의 개수가 `max_thread_pool`를 초과하거나 WAITING/BLOCKED 상태의 스레드가 많은 상태
- **확인 필요**: 출력이 없거나 jstack 수행 불가 및 실행불가(권한/미설치 등)로 점검 불가한 상태