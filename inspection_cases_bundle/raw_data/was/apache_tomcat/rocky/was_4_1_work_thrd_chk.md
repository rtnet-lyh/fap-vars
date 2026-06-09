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
netstat -ntp | grep -E '8080|8009' | awk '{print $6}' | sort | uniq -c
```

# 출력 결과
```text
[OS: Rocky 9.4] 추출된 결과입니다.
[root@re-test-POTAL logs]# pwd
/home/koem01/apache-tomcat-8.0.32/logs
[root@re-test-POTAL logs]# cat gc_2026-06-05_10-40-58.log.0.current
OpenJDK 64-Bit Server VM (25.412-b08) for linux-amd64 JRE (1.8.0_412-b08), built on Apr 18 2024 00:00:00 by "mockbuild" with gcc 11.4.1 20230605 (Red Hat 11.4.1-2)
Memory: 4k page, physical 7869564k(4072652k free), swap 4141052k(4128764k free)
CommandLine flags: -XX:GCLogFileSize=10485760 -XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=/home/koem01/apache-tomcat-8.0.32/dump -XX:InitialHeapSize=8589934592 -XX:MaxHeapSize=8589934592 -XX:NewRatio=2 -XX:NumberOfGCLogFiles=15 -XX:+PrintGC -XX:+PrintGCDateStamps -XX:+PrintGCDetails -XX:+PrintGCTimeStamps -XX:+UseCompressedClassPointers -XX:+UseCompressedOops -XX:+UseGCLogFileRotation -XX:+UseParallelGC
2026-06-05T10:41:03.443+0900: 5.378: [GC (Allocation Failure) [PSYoungGen: 2097664K->329994K(2446848K)] 2097664K->330082K(8039424K), 0.1464274 secs] [Times: user=0.13 sys=0.07, real=0.15 secs]
2026-06-05T10:41:04.197+0900: 6.132: [GC (Metadata GC Threshold) [PSYoungGen: 812481K->137042K(2446848K)] 812569K->137130K(8039424K), 0.0564239 secs] [Times: user=0.05 sys=0.04, real=0.05 secs]
2026-06-05T10:41:04.254+0900: 6.189: [Full GC (Metadata GC Threshold) [PSYoungGen: 137042K->0K(2446848K)] [ParOldGen: 88K->130864K(5592576K)] 137130K->130864K(8039424K), [Metaspace: 20697K->20697K(1069056K)], 0.1911137 secs] [Times: user=0.23 sys=0.03, real=0.19 secs]
2026-06-05T10:41:05.141+0900: 7.076: [GC (Metadata GC Threshold) [PSYoungGen: 161534K->15790K(2446848K)] 292398K->146663K(8039424K), 0.0069937 secs] [Times: user=0.02 sys=0.00, real=0.01 secs]
2026-06-05T10:41:05.148+0900: 7.083: [Full GC (Metadata GC Threshold) [PSYoungGen: 15790K->0K(2446848K)] [ParOldGen: 130872K->89253K(5592576K)] 146663K->89253K(8039424K), [Metaspace: 34718K->34718K(1079296K)], 0.0557997 secs] [Times: user=0.09 sys=0.00, real=0.05 secs]
2026-06-05T10:41:07.842+0900: 9.777: [GC (Allocation Failure) [PSYoungGen: 2097664K->60653K(2446848K)] 2186917K->149906K(8039424K), 0.0331319 secs] [Times: user=0.06 sys=0.00, real=0.03 secs]
2026-06-05T10:41:09.157+0900: 11.091: [GC (Metadata GC Threshold) [PSYoungGen: 967170K->74760K(2446848K)] 1056423K->164021K(8039424K), 0.0389129 secs] [Times: user=0.07 sys=0.00, real=0.04 secs]
2026-06-05T10:41:09.196+0900: 11.130: [Full GC (Metadata GC Threshold) [PSYoungGen: 74760K->0K(2446848K)] [ParOldGen: 89261K->154043K(5592576K)] 164021K->154043K(8039424K), [Metaspace: 58280K->58280K(1101824K)], 0.2822879 secs] [Times: user=0.51 sys=0.01, real=0.29 secs]

---
```

# 설명
- `netstat -ntp` 명령어를 사용하여 WAS 서비스 포트(8080/8009) 혹은 DB 포트(3306)에 연결된 네트워크 세션의 상태(ESTABLISHED, CLOSE_WAIT 등) 통계를 확인합니다. 이를 통해 워커 스레드나 커넥션 풀의 고갈 여부를 파악합니다.

# 임계치
max_established_conn: 서비스 및 DB 커넥션 풀의 최대 허용 한계치

# 판단기준
- **양호**: 활성화된 연결(ESTABLISHED) 수가 임계치 내에서 안정적으로 관리됨
- **경고**: 연결 수가 한계치에 도달하거나, 반환되지 않는 `CLOSE_WAIT` 상태가 다수 누적됨
- **확인 필요**: 명령어 오류 또는 수집된 네트워크 통계 결과와 포맷이 달라 점검이 불가한 상태
