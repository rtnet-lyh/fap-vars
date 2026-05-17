# 영역
Dump 파일

# 세부 점검항목
Dump 파일 점검

# 점검 내용
메모리공간 부족으로 인한 Error 발생 시 생성되는 HeapDump 파일 발생여부 확인(기설정된 Dump 옵션으로 Heap의 높은 사용량을 만든 원인을 분석하기 위함)

# 구분
필수

# 명령어 jeus_log_path: /home/exTMS/tmax/jeus/log
```bash
for pid in $(ps -ef | grep "jeus.server.ServerBootstrapper" | grep -v grep | awk '{print $2}'); do echo "======== PID: $pid ========"; jcmd $pid VM.flags; done;
```

# 출력 결과
```text
[exTMS@tips_was2:/LOG/exTMS/tmax/jeus/log/extms2/servlet]$ for pid in $(ps -ef | grep "jeus.server.ServerBootstrapper" | grep -v grep | awk '{print $2}'); do echo "======== PID: $pid ========"; jcmd $pid VM.flags; done;
======== PID: 1516108 ========
1516108:
-XX:CICompilerCount=4 -XX:CompressedClassSpaceSize=528482304 -XX:ConcGCThreads=3 -XX:G1HeapRegionSize=4194304 -XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=/LOG/exTMS/tmax/jeus/log/dump/ -XX:InitialHeapSize=8589934592 -XX:LogFile=/LOG/exTMS/tmax/jeus/log/trafficMonitor2/jvm.log -XX:+LogVMOutput -XX:MarkStackSize=4194304 -XX:MaxGCPauseMillis=200 -XX:MaxHeapSize=8589934592 -XX:MaxMetaspaceSize=536870912 -XX:MaxNewSize=5150605312 -XX:MetaspaceSize=536870912 -XX:MinHeapDeltaBytes=4194304 -XX:+PrintGC -XX:+PrintGCDateStamps -XX:+PrintGCDetails -XX:+PrintGCTimeStamps -XX:+PrintHeapAtGC -XX:+UnlockDiagnosticVMOptions -XX:+UseCompressedClassPointers -XX:+UseCompressedOops -XX:+UseFastUnorderedTimeStamps -XX:+UseG1GC
======== PID: 1664513 ========
1664513:
-XX:CICompilerCount=4 -XX:CompressedClassSpaceSize=528482304 -XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=/LOG/exTMS/tmax/jeus/log/dump/ -XX:InitialHeapSize=4294967296 -XX:LogFile=/LOG/exTMS/tmax/jeus/log/extms2/jvm.log -XX:+LogVMOutput -XX:MaxHeapSize=4294967296 -XX:MaxMetaspaceSize=536870912 -XX:MaxNewSize=1431306240 -XX:MetaspaceSize=536870912 -XX:MinHeapDeltaBytes=524288 -XX:NewSize=1431306240 -XX:OldSize=2863661056 -XX:+PrintGC -XX:+PrintGCDateStamps -XX:+PrintGCDetails -XX:+PrintGCTimeStamps -XX:+PrintHeapAtGC -XX:+UnlockDiagnosticVMOptions -XX:+UseCompressedClassPointers -XX:+UseCompressedOops -XX:+UseFastUnorderedTimeStamps -XX:+UseParallelGC
```

# 설명
- JVM 옵션 확인: JVM이 힙 덤프를 생성하도록 설정되어 있는지 확인. -XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=/path/to/dump 이 옵션이 설정되어 있으면, 메모리 부족 오류가 발생했을 때 힙 덤프가 지정된 경로에 생성되며, 힙 덤프 파일이 생성되었는지 확인하려면 해당 디렉토리에서 덤프 파일을 검색. 예를 들어, ls -l /path/to/dump | grep .hprof 
- JVM 옵션 확인: JVM이 메모리 부족 시 힙 덤프를 생성하도록 설정되어 있는지 확인 -XX:+HeapDumpOnOutOfMemoryError 옵션이 포함되어 있어야 하며, 옵션이 없으면 추가 후 서버 재시작 필요 
--> 파일 시스템에서 확인: 지정된 디렉토리에서 .hprof 파일을 검색하여 힙 덤프가 생성되었는지 확인하여, 파일이 없으면 JVM 설정 검토 필요
--> 로그 파일에서 확인: JBoss 로그에서 OutOfMemoryError 발생 시 힙 덤프 생성 관련 메시지를 검색하여, 메시지가 있다면 생성된 파일의 경로를 확인하고 문제 분석 필요

# 임계치


# 판단기준 - 수동 확인 필요
- **양호**: 출력에 -XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=/path/to/dump 설정이 포함 되어있는 상태
- **경고**: 출력에 -XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=/path/to/dump 설정이 포함 되어있지 않은 상태
- **확인 필요**: 출력이 없거나 jcmd 명령어 실행불가(권한/미설치 등)로 점검 불가한 상태