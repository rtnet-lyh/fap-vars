# 영역
JVM Heap Memory

# 세부 점검항목
동적 메모리영역 점검

# 점검 내용
Java Heapmemory 여유공간 확인(객체 데이터 저장 공간인 Heap영역 공간 부족 시 발생 할수 있는 서비스 중단 등의 오류 상황 예방을 위한 점검)

# 구분
권고

# 명령어
```bash
for pid in $(ps -ef | grep "jeus.server.ServerBootstrapper" | grep -v grep | awk '{print $2}'); do echo "======== PID: $pid ========"; jmap -heap $pid; echo; done
```

# 출력 결과
```text
[root@tips_was1 ~]# for pid in $(ps -ef | grep "jeus.server.ServerBootstrapper" | grep -v grep | awk '{print $2}'); do echo "======== PID: $pid ========"; jmap -heap $pid; echo; done
======== PID: 1385334 ========
Attaching to process ID 1385334, please wait...
Debugger attached successfully.
Server compiler detected.
JVM version is 25.431-b10

using thread-local object allocation.
Garbage-First (G1) GC with 10 thread(s)

Heap Configuration:
   MinHeapFreeRatio         = 40
   MaxHeapFreeRatio         = 70
   MaxHeapSize              = 8589934592 (8192.0MB)
   NewSize                  = 1363144 (1.2999954223632812MB)
   MaxNewSize               = 5150605312 (4912.0MB)
   OldSize                  = 5452592 (5.1999969482421875MB)
   NewRatio                 = 2
   SurvivorRatio            = 8
   MetaspaceSize            = 536870912 (512.0MB)
   CompressedClassSpaceSize = 528482304 (504.0MB)
   MaxMetaspaceSize         = 536870912 (512.0MB)
   G1HeapRegionSize         = 4194304 (4.0MB)

Heap Usage:
G1 Heap:
   regions  = 2048
   capacity = 8589934592 (8192.0MB)
   used     = 3874552064 (3695.060791015625MB)
   free     = 4715382528 (4496.939208984375MB)
   45.105722546577454% used
G1 Young Generation:
Eden Space:
   regions  = 548
   capacity = 5087690752 (4852.0MB)
   used     = 2298478592 (2192.0MB)
   free     = 2789212160 (2660.0MB)
   45.17724649629019% used
Survivor Space:
   regions  = 11
   capacity = 46137344 (44.0MB)
   used     = 46137344 (44.0MB)
   free     = 0 (0.0MB)
   100.0% used
G1 Old Generation:
   regions  = 366
   capacity = 3456106496 (3296.0MB)
   used     = 1525741824 (1455.060791015625MB)
   free     = 1930364672 (1840.939208984375MB)
   44.14626186333814% used

48809 interned Strings occupying 4849784 bytes.

======== PID: 1416324 ========
Attaching to process ID 1416324, please wait...
Debugger attached successfully.
Server compiler detected.
JVM version is 25.431-b10

using thread-local object allocation.
Parallel GC with 10 thread(s)

Heap Configuration:
   MinHeapFreeRatio         = 0
   MaxHeapFreeRatio         = 100
   MaxHeapSize              = 4294967296 (4096.0MB)
   NewSize                  = 1431306240 (1365.0MB)
   MaxNewSize               = 1431306240 (1365.0MB)
   OldSize                  = 2863661056 (2731.0MB)
   NewRatio                 = 2
   SurvivorRatio            = 8
   MetaspaceSize            = 536870912 (512.0MB)
   CompressedClassSpaceSize = 528482304 (504.0MB)
   MaxMetaspaceSize         = 536870912 (512.0MB)
   G1HeapRegionSize         = 0 (0.0MB)

Heap Usage:
PS Young Generation
Eden Space:
   capacity = 1401421824 (1336.5MB)
   used     = 594508120 (566.9671249389648MB)
   free     = 806913704 (769.5328750610352MB)
   42.421782636660296% used
From Space:
   capacity = 14680064 (14.0MB)
   used     = 5926632 (5.652076721191406MB)
   free     = 8753432 (8.347923278808594MB)
   40.37197657993862% used
To Space:
   capacity = 14155776 (13.5MB)
   used     = 0 (0.0MB)
   free     = 14155776 (13.5MB)
   0.0% used
PS Old Generation
   capacity = 2863661056 (2731.0MB)
   used     = 311900208 (297.4512176513672MB)
   free     = 2551760848 (2433.548782348633MB)
   10.891659379398286% used

59521 interned Strings occupying 9351792 bytes.
```

# 설명
- Heap Configuration: JVM 힙 메모리 설정 값은 시스템 메모리 자원과 애플리케이션 요구 사항에 맞게 적절히 구성되어야 하며, MaxHeapSize는 일반적으로 전체 메모리의 75%를 넘지 않도록 설정해야 성능 저하를 방지할 수 있음. 힙 메모리 크기가 적절하지 않으면 JVM 설정을 수정. 
- 전체 힙 메모리에서 몇 퍼센트를 쓰고 있는지 계산하려면, 사용 중인 힙 메모리와 최대 힙 메모리(MaxHeapSize)를 비교하면 됨. 사용 중인 메모리는 Old Generation와 New Generation(Eden Space + Survivor Space)를 합산하여 알 수 있음. 
- 위 출력값을 예로 들어 계산해본다면, Old Generation은 731.09MB, New Generation은 269.34MB를 사용 중이므로 총 1000.43MB를 사용하고 있고, MaxHeapSize는 2000MB이므로, ( Used Heap Memory / MaxHeapSize ) × 100 = (1000.43 / 2000) × 100 ≈ 50.02% 만큼 사용 중인 것을 알 수 있음. 

# 임계치
max_heap_size: 최대 힙 메모리 크기


# 판단기준
- **양호**: MaxHeapSize가 전체 메모리의 `max_heap_size`를 초과하지 않는 상태
- **경고**: MaxHeapSize가 전체 메모리의 `max_heap_size`를 초과한 상태
- **확인 필요**: 출력이 없거나 jmap 수행 불가 및 실행불가(권한/미설치 등)로 점검 불가한 상태