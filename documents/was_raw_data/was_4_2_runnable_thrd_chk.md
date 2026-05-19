# 영역
Thread Pool 상태

# 세부 점검항목
장기수행 작업 확인

# 점검 내용
오랜시간 동안 적체 중인 Thread 존재 유무 확인(스레드 여유 공간 확보를 위해 Tranjaction의 비정상적인 종료, DB Table 오류 등으로 인한 비정상적으로 장시간 적체 중인 스레드를 확인)

# 구분
필수

# 명령어
```bash
for pid in $(ps -ef | grep "jeus.server.ServerBootstrapper" | grep -v grep | awk '{print $2}'); do echo "======== PID: $pid ========"; jstack 1559740 | awk '/^"/{t=$0} /Thread.State: RUNNABLE/{print t "\n" $0 "\n"}'; done;
```

# 출력 결과
```text
[root@tips_was1 ~]# for pid in $(ps -ef | grep "jeus.server.ServerBootstrapper" | grep -v grep | awk '{print $2}'); do echo "======== PID: $pid ========"; jstack 1559740 | awk '/^"/{t=$0} /Thread.State: RUNNABLE/{print t "\n" $0 "\n"}'; done;
======== PID: 1559740 ========
"Attach Listener" #192 daemon prio=9 os_prio=0 tid=0x00007ff900001800 nid=0x17fcf0 waiting on condition [0x0000000000000000]
   java.lang.Thread.State: RUNNABLE

"webtob2-hth0-50" #173 daemon prio=5 os_prio=0 tid=0x00007ff968fbc800 nid=0x17cd86 runnable [0x00007ff7ba5e4000]
   java.lang.Thread.State: RUNNABLE

======== PID: 1567015 ========
"Attach Listener" #192 daemon prio=9 os_prio=0 tid=0x00007ff900001800 nid=0x17fcf0 waiting on condition [0x0000000000000000]
   java.lang.Thread.State: RUNNABLE

"webtob2-hth0-50" #173 daemon prio=5 os_prio=0 tid=0x00007ff968fbc800 nid=0x17cd86 runnable [0x00007ff7ba5e4000]
   java.lang.Thread.State: RUNNABLE

```

# 설명
- Thread State ("RUNNABLE"): 스레드가 CPU에서 실행 중인 상태를 나타내며, RUNNABLE 상태에서 오랫동안 유지되면 작업이 정상적으로 종료되지 않았을 가능성이 있음. 대부분의 스레드는 일정 시간 내에 종료되어야 하며, 스레드가 지나치게 오래 RUNNABLE 상태에 있으면 스레드 풀 설정을 조정하거나 작업 성능을 최적화하는 것이 필요. 
- Execution Time: 스레드가 특정 작업을 수행하는 데 걸리는 시간을 통해 실행 시간이 비정상적으로 길어지면 애플리케이션 성능에 악영향을 미칠 수 있으므로 성능 분석을 통해 작업을 최적화하고, 필요 시 작업을 분할하거나 스레드 수를 조정하는 것이 필요.

# 임계치
max_runnable_thread_pool: 오랜 시간 적체 중인 최대 스레드 풀 개수


# 판단기준
- **양호**: 출력된 스레드명의 개수가 `max_runnable_thread_pool`를 초과하지 않고 WAITING/BLOCKED 상태의 스레드가 적은 상태
- **경고**: 출력된 스레드명의 개수가 `max_runnable_thread_pool`를 초과하거나 WAITING/BLOCKED 상태의 스레드가 많은 상태
- **확인 필요**: 출력이 없거나 jstack 수행 불가 및 실행불가(권한/미설치 등)로 점검 불가한 상태