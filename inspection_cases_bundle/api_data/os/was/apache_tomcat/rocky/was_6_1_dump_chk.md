# type_name

일상점검

# area_name

was

# category_name

상태점검

# application_type

apache_tomcat

# application

rocky

# inspection_code


WAS-TOM-RKY-014

# is_required

필수

# inspection_name

Dump 파일 점검

# inspection_content

메모리공간 부족으로 인한 Error 발생 시 생성되는 HeapDump 파일 발생여부 확인(기설정된 Dump 옵션으로 Heap의 높은 사용량을 만든 원인을 분석하기 위함)

# inspection_command

```bash
find /home/koem01/apache-tomcat-8.0.32/ -name "*.hprof" -o -name "core.*"
```

# inspection_output

```text
[OS: Rocky 9.4] 추출된 결과입니다.
[root@re-test-POTAL logs]# /home/koem01/elasticsearch-7.6.2/jdk/bin/jstack $(pgrep -f 'org.apache.catalina.startup.Bootstrap')
2026-06-05 11:01:48
Full thread dump OpenJDK 64-Bit Server VM (25.412-b08 mixed mode):

"Attach Listener" #30 daemon prio=9 os_prio=0 tid=0x00007fcdb8001800 nid=0xb268c waiting on condition [0x0000000000000000]
   java.lang.Thread.State: RUNNABLE

"ajp-nio-8009-Acceptor-0" #28 daemon prio=5 os_prio=0 tid=0x00007fce0457e000 nid=0xb2080 runnable [0x00007fcddc174000]
   java.lang.Thread.State: RUNNABLE
        at sun.nio.ch.ServerSocketChannelImpl.accept0(Native Method)
        at sun.nio.ch.ServerSocketChannelImpl.accept(ServerSocketChannelImpl.java:421)
        at sun.nio.ch.ServerSocketChannelImpl.accept(ServerSocketChannelImpl.java:249)
        - locked <0x00000005c01b3a38> (a java.lang.Object)
        at org.apache.tomcat.util.net.NioEndpoint$Acceptor.run(NioEndpoint.java:682)
        at java.lang.Thread.run(Thread.java:750)

"ajp-nio-8009-ClientPoller-1" #27 daemon prio=5 os_prio=0 tid=0x00007fce0457c000 nid=0xb207f runnable [0x00007fcddd272000]
   java.lang.Thread.State: RUNNABLE
        at sun.nio.ch.EPollArrayWrapper.epollWait(Native Method)
        at sun.nio.ch.EPollArrayWrapper.poll(EPollArrayWrapper.java:269)
        at sun.nio.ch.EPollSelectorImpl.doSelect(EPollSelectorImpl.java:93)
        at sun.nio.ch.SelectorImpl.lockAndDoSelect(SelectorImpl.java:86)
        - locked <0x000000072121c7b8> (a sun.nio.ch.Util$3)
        - locked <0x000000072121c7a8> (a java.util.Collections$UnmodifiableSet)
        - locked <0x000000072121c690> (a sun.nio.ch.EPollSelectorImpl)
        at sun.nio.ch.SelectorImpl.select(SelectorImpl.java:97)
        at org.apache.tomcat.util.net.NioEndpoint$Poller.run(NioEndpoint.java:1034)
        at java.lang.Thread.run(Thread.java:750)

"ajp-nio-8009-ClientPoller-0" #26 daemon prio=5 os_prio=0 tid=0x00007fce0457a000 nid=0xb207e runnable [0x00007fcddd372000]
   java.lang.Thread.State: RUNNABLE
        at sun.nio.ch.EPollArrayWrapper.epollWait(Native Method)
        at sun.nio.ch.EPollArrayWrapper.poll(EPollArrayWrapper.java:269)
        at sun.nio.ch.EPollSelectorImpl.doSelect(EPollSelectorImpl.java:93)
        at sun.nio.ch.SelectorImpl.lockAndDoSelect(SelectorImpl.java:86)
        - locked <0x000000072120bee0> (a sun.nio.ch.Util$3)
        - locked <0x000000072120bed0> (a java.util.Collections$UnmodifiableSet)
        - locked <0x000000072120bdb8> (a sun.nio.ch.EPollSelectorImpl)
        at sun.nio.ch.SelectorImpl.select(SelectorImpl.java:97)
        at org.apache.tomcat.util.net.NioEndpoint$Poller.run(NioEndpoint.java:1034)
        at java.lang.Thread.run(Thread.java:750)

"http-nio-8090-Acceptor-0" #25 daemon prio=5 os_prio=0 tid=0x00007fce0413a000 nid=0xb207d runnable [0x00007fcddd472000]
   java.lang.Thread.State: RUNNABLE
        at sun.nio.ch.ServerSocketChannelImpl.accept0(Native Method)
        at sun.nio.ch.ServerSocketChannelImpl.accept(ServerSocketChannelImpl.java:421)
        at sun.nio.ch.ServerSocketChannelImpl.accept(ServerSocketChannelImpl.java:249)
        - locked <0x00000005c0340800> (a java.lang.Object)
        at org.apache.tomcat.util.net.NioEndpoint$Acceptor.run(NioEndpoint.java:682)
        at java.lang.Thread.run(Thread.java:750)

"http-nio-8090-ClientPoller-1" #24 daemon prio=5 os_prio=0 tid=0x00007fce04138000 nid=0xb207c runnable [0x00007fcddd572000]
   java.lang.Thread.State: RUNNABLE
        at sun.nio.ch.EPollArrayWrapper.epollWait(Native Method)
        at sun.nio.ch.EPollArrayWrapper.poll(EPollArrayWrapper.java:269)
        at sun.nio.ch.EPollSelectorImpl.doSelect(EPollSelectorImpl.java:93)
        at sun.nio.ch.SelectorImpl.lockAndDoSelect(SelectorImpl.java:86)
        - locked <0x00000007211f9770> (a sun.nio.ch.Util$3)
        - locked <0x00000007211f9760> (a java.util.Collections$UnmodifiableSet)
        - locked <0x00000007211f9648> (a sun.nio.ch.EPollSelectorImpl)
        at sun.nio.ch.SelectorImpl.select(SelectorImpl.java:97)
        at org.apache.tomcat.util.net.NioEndpoint$Poller.run(NioEndpoint.java:1034)
        at java.lang.Thread.run(Thread.java:750)

"http-nio-8090-ClientPoller-0" #23 daemon prio=5 os_prio=0 tid=0x00007fce04136800 nid=0xb207b runnable [0x00007fcddd672000]
   java.lang.Thread.State: RUNNABLE
        at sun.nio.ch.EPollArrayWrapper.epollWait(Native Method)
        at sun.nio.ch.EPollArrayWrapper.poll(EPollArrayWrapper.java:269)
        at sun.nio.ch.EPollSelectorImpl.doSelect(EPollSelectorImpl.java:93)
        at sun.nio.ch.SelectorImpl.lockAndDoSelect(SelectorImpl.java:86)
        - locked <0x00000007211e8e98> (a sun.nio.ch.Util$3)
        - locked <0x00000007211e8e88> (a java.util.Collections$UnmodifiableSet)
        - locked <0x00000007211e8d70> (a sun.nio.ch.EPollSelectorImpl)
        at sun.nio.ch.SelectorImpl.select(SelectorImpl.java:97)
        at org.apache.tomcat.util.net.NioEndpoint$Poller.run(NioEndpoint.java:1034)
        at java.lang.Thread.run(Thread.java:750)

"http-nio-8443-Acceptor-0" #22 daemon prio=5 os_prio=0 tid=0x00007fce04135000 nid=0xb207a runnable [0x00007fcddd772000]
   java.lang.Thread.State: RUNNABLE
        at sun.nio.ch.ServerSocketChannelImpl.accept0(Native Method)
        at sun.nio.ch.ServerSocketChannelImpl.accept(ServerSocketChannelImpl.java:421)
        at sun.nio.ch.ServerSocketChannelImpl.accept(ServerSocketChannelImpl.java:249)
        - locked <0x00000005c0342570> (a java.lang.Object)
        at org.apache.tomcat.util.net.NioEndpoint$Acceptor.run(NioEndpoint.java:682)
        at java.lang.Thread.run(Thread.java:750)

"http-nio-8443-ClientPoller-1" #21 daemon prio=5 os_prio=0 tid=0x00007fce04133800 nid=0xb2079 runnable [0x00007fcddd872000]
   java.lang.Thread.State: RUNNABLE
        at sun.nio.ch.EPollArrayWrapper.epollWait(Native Method)
        at sun.nio.ch.EPollArrayWrapper.poll(EPollArrayWrapper.java:269)
        at sun.nio.ch.EPollSelectorImpl.doSelect(EPollSelectorImpl.java:93)
        at sun.nio.ch.SelectorImpl.lockAndDoSelect(SelectorImpl.java:86)
        - locked <0x00000007211d0ad0> (a sun.nio.ch.Util$3)
        - locked <0x00000007211d0ac0> (a java.util.Collections$UnmodifiableSet)
        - locked <0x00000007211d09a8> (a sun.nio.ch.EPollSelectorImpl)
        at sun.nio.ch.SelectorImpl.select(SelectorImpl.java:97)
        at org.apache.tomcat.util.net.NioEndpoint$Poller.run(NioEndpoint.java:1034)
        at java.lang.Thread.run(Thread.java:750)

"http-nio-8443-ClientPoller-0" #20 daemon prio=5 os_prio=0 tid=0x00007fce0416f000 nid=0xb2078 runnable [0x00007fcddd972000]
   java.lang.Thread.State: RUNNABLE
        at sun.nio.ch.EPollArrayWrapper.epollWait(Native Method)
        at sun.nio.ch.EPollArrayWrapper.poll(EPollArrayWrapper.java:269)
        at sun.nio.ch.EPollSelectorImpl.doSelect(EPollSelectorImpl.java:93)
        at sun.nio.ch.SelectorImpl.lockAndDoSelect(SelectorImpl.java:86)
        - locked <0x00000007211c0160> (a sun.nio.ch.Util$3)
        - locked <0x00000007211c0150> (a java.util.Collections$UnmodifiableSet)
        - locked <0x00000007211c0038> (a sun.nio.ch.EPollSelectorImpl)
        at sun.nio.ch.SelectorImpl.select(SelectorImpl.java:97)
        at org.apache.tomcat.util.net.NioEndpoint$Poller.run(NioEndpoint.java:1034)
        at java.lang.Thread.run(Thread.java:750)

"ContainerBackgroundProcessor[StandardEngine[Catalina]]" #19 daemon prio=5 os_prio=0 tid=0x00007fce045f4000 nid=0xb2077 waiting on condition [0x00007fcddc4fb000]
   java.lang.Thread.State: TIMED_WAITING (sleeping)
        at java.lang.Thread.sleep(Native Method)
        at org.apache.catalina.core.ContainerBase$ContainerBackgroundProcessor.run(ContainerBase.java:1344)
        at java.lang.Thread.run(Thread.java:750)

"NioBlockingSelector.BlockPoller-3" #14 daemon prio=5 os_prio=0 tid=0x00007fce0470e000 nid=0xb2070 runnable [0x00007fcddde9f000]
   java.lang.Thread.State: RUNNABLE
        at sun.nio.ch.EPollArrayWrapper.epollWait(Native Method)
        at sun.nio.ch.EPollArrayWrapper.poll(EPollArrayWrapper.java:269)
        at sun.nio.ch.EPollSelectorImpl.doSelect(EPollSelectorImpl.java:93)
        at sun.nio.ch.SelectorImpl.lockAndDoSelect(SelectorImpl.java:86)
        - locked <0x00000005c01b2f20> (a sun.nio.ch.Util$3)
        - locked <0x00000005c01b2f10> (a java.util.Collections$UnmodifiableSet)
        - locked <0x00000005c01b2dd8> (a sun.nio.ch.EPollSelectorImpl)
        at sun.nio.ch.SelectorImpl.select(SelectorImpl.java:97)
        at org.apache.tomcat.util.net.NioBlockingSelector$BlockPoller.run(NioBlockingSelector.java:342)

"NioBlockingSelector.BlockPoller-2" #13 daemon prio=5 os_prio=0 tid=0x00007fce046f3800 nid=0xb206f runnable [0x00007fcdddf9f000]
   java.lang.Thread.State: RUNNABLE
        at sun.nio.ch.EPollArrayWrapper.epollWait(Native Method)
        at sun.nio.ch.EPollArrayWrapper.poll(EPollArrayWrapper.java:269)
        at sun.nio.ch.EPollSelectorImpl.doSelect(EPollSelectorImpl.java:93)
        at sun.nio.ch.SelectorImpl.lockAndDoSelect(SelectorImpl.java:86)
        - locked <0x00000005c01b4dd0> (a sun.nio.ch.Util$3)
        - locked <0x00000005c01b4dc0> (a java.util.Collections$UnmodifiableSet)
        - locked <0x00000005c01b4c98> (a sun.nio.ch.EPollSelectorImpl)
        at sun.nio.ch.SelectorImpl.select(SelectorImpl.java:97)
        at org.apache.tomcat.util.net.NioBlockingSelector$BlockPoller.run(NioBlockingSelector.java:342)

"NioBlockingSelector.BlockPoller-1" #12 daemon prio=5 os_prio=0 tid=0x00007fce046da000 nid=0xb206e runnable [0x00007fcdde09f000]
   java.lang.Thread.State: RUNNABLE
        at sun.nio.ch.EPollArrayWrapper.epollWait(Native Method)
        at sun.nio.ch.EPollArrayWrapper.poll(EPollArrayWrapper.java:269)
        at sun.nio.ch.EPollSelectorImpl.doSelect(EPollSelectorImpl.java:93)
        at sun.nio.ch.SelectorImpl.lockAndDoSelect(SelectorImpl.java:86)
        - locked <0x00000005c0341da8> (a sun.nio.ch.Util$3)
        - locked <0x00000005c0341d98> (a java.util.Collections$UnmodifiableSet)
        - locked <0x00000005c0341c70> (a sun.nio.ch.EPollSelectorImpl)
        at sun.nio.ch.SelectorImpl.select(SelectorImpl.java:97)
        at org.apache.tomcat.util.net.NioBlockingSelector$BlockPoller.run(NioBlockingSelector.java:342)

"GC Daemon" #11 daemon prio=2 os_prio=0 tid=0x00007fce045c3000 nid=0xb206d in Object.wait() [0x00007fcdde61f000]
   java.lang.Thread.State: TIMED_WAITING (on object monitor)
        at java.lang.Object.wait(Native Method)
        - waiting on <0x00000005c05864f0> (a sun.misc.GC$LatencyLock)
        at sun.misc.GC$Daemon.run(GC.java:117)
        - locked <0x00000005c05864f0> (a sun.misc.GC$LatencyLock)

"AsyncFileHandlerWriter-723074861" #10 daemon prio=5 os_prio=0 tid=0x00007fce04204000 nid=0xb206c waiting on condition [0x00007fcddeb87000]
   java.lang.Thread.State: TIMED_WAITING (parking)
        at sun.misc.Unsafe.park(Native Method)
        - parking to wait for  <0x00000005c044e468> (a java.util.concurrent.locks.AbstractQueuedSynchronizer$ConditionObject)
        at java.util.concurrent.locks.LockSupport.parkNanos(LockSupport.java:215)
        at java.util.concurrent.locks.AbstractQueuedSynchronizer$ConditionObject.awaitNanos(AbstractQueuedSynchronizer.java:2078)
        at java.util.concurrent.LinkedBlockingDeque.pollFirst(LinkedBlockingDeque.java:522)
        at java.util.concurrent.LinkedBlockingDeque.poll(LinkedBlockingDeque.java:684)
        at org.apache.juli.AsyncFileHandler$LoggerThread.run(AsyncFileHandler.java:145)

"Service Thread" #7 daemon prio=9 os_prio=0 tid=0x00007fce0412c000 nid=0xb206a runnable [0x0000000000000000]
   java.lang.Thread.State: RUNNABLE

"C1 CompilerThread1" #6 daemon prio=9 os_prio=0 tid=0x00007fce0411f000 nid=0xb2069 waiting on condition [0x0000000000000000]
   java.lang.Thread.State: RUNNABLE

"C2 CompilerThread0" #5 daemon prio=9 os_prio=0 tid=0x00007fce0411d000 nid=0xb2068 waiting on condition [0x0000000000000000]
   java.lang.Thread.State: RUNNABLE

"Signal Dispatcher" #4 daemon prio=9 os_prio=0 tid=0x00007fce0410e000 nid=0xb2067 runnable [0x0000000000000000]
   java.lang.Thread.State: RUNNABLE

"Finalizer" #3 daemon prio=8 os_prio=0 tid=0x00007fce040e2000 nid=0xb2066 in Object.wait() [0x00007fcddf1ee000]
   java.lang.Thread.State: WAITING (on object monitor)
        at java.lang.Object.wait(Native Method)
        - waiting on <0x00000005c0586cb8> (a java.lang.ref.ReferenceQueue$Lock)
        at java.lang.ref.ReferenceQueue.remove(ReferenceQueue.java:144)
        - locked <0x00000005c0586cb8> (a java.lang.ref.ReferenceQueue$Lock)
        at java.lang.ref.ReferenceQueue.remove(ReferenceQueue.java:165)
        at java.lang.ref.Finalizer$FinalizerThread.run(Finalizer.java:188)

"Reference Handler" #2 daemon prio=10 os_prio=0 tid=0x00007fce040dd800 nid=0xb2065 in Object.wait() [0x00007fcddf2ee000]
   java.lang.Thread.State: WAITING (on object monitor)
        at java.lang.Object.wait(Native Method)
        - waiting on <0x00000005c0a09c08> (a java.lang.ref.Reference$Lock)
        at java.lang.Object.wait(Object.java:502)
        at java.lang.ref.Reference.tryHandlePending(Reference.java:191)
        - locked <0x00000005c0a09c08> (a java.lang.ref.Reference$Lock)
        at java.lang.ref.Reference$ReferenceHandler.run(Reference.java:153)

"main" #1 prio=5 os_prio=0 tid=0x00007fce0404d000 nid=0xb2061 runnable [0x00007fce0b9fd000]
   java.lang.Thread.State: RUNNABLE
        at java.net.PlainSocketImpl.socketAccept(Native Method)
        at java.net.AbstractPlainSocketImpl.accept(AbstractPlainSocketImpl.java:409)
        at java.net.ServerSocket.implAccept(ServerSocket.java:560)
        at java.net.ServerSocket.accept(ServerSocket.java:528)
        at org.apache.catalina.core.StandardServer.await(StandardServer.java:446)
        at org.apache.catalina.startup.Catalina.await(Catalina.java:717)
        at org.apache.catalina.startup.Catalina.start(Catalina.java:663)
        at sun.reflect.NativeMethodAccessorImpl.invoke0(Native Method)
        at sun.reflect.NativeMethodAccessorImpl.invoke(NativeMethodAccessorImpl.java:62)
        at sun.reflect.DelegatingMethodAccessorImpl.invoke(DelegatingMethodAccessorImpl.java:43)
        at java.lang.reflect.Method.invoke(Method.java:498)
        at org.apache.catalina.startup.Bootstrap.start(Bootstrap.java:351)
        at org.apache.catalina.startup.Bootstrap.main(Bootstrap.java:485)

"VM Thread" os_prio=0 tid=0x00007fce040d4000 nid=0xb2064 runnable

"GC task thread#0 (ParallelGC)" os_prio=0 tid=0x00007fce0405b000 nid=0xb2062 runnable

"GC task thread#1 (ParallelGC)" os_prio=0 tid=0x00007fce0405d000 nid=0xb2063 runnable

"VM Periodic Task Thread" os_prio=0 tid=0x00007fce0412e800 nid=0xb206b waiting on condition

JNI global references: 353

---
```

# description

- WAS 프로세스의 비정상 종료나 메모리 고갈 시 생성되는 `*.hprof`, `core.*` 파일의 신규 생성 여부를 확인하여 심각한 장애 발생 이력을 점검합니다.

- **양호**: 점검 기간 내에 새롭게 생성된 비정상 종료 덤프 파일이 없음
- **경고**: 시스템 장애로 인한 신규 덤프 파일이 발견됨
- **확인 필요**: find 명령어 권한 부족 또는 디렉토리 경로 오류로 확인 불가한 상태

# thresholds

[
    {id: null, key: "max_dump_count", value: "0", sortOrder: 0}
]

# inspection_script

# -*- coding: utf-8 -*-

from .common._base import BaseCheck


COMMAND = 'find /home/koem01/apache-tomcat-8.0.32/ -name "*.hprof" -o -name "core.*"'
COMMAND_TIMEOUT = 20


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'linux'
    PARAMIKO_REUSE_SESSION = False

    def run(self):
        result = self._run_paramiko_commands(
            [{'command': COMMAND, 'timeout': COMMAND_TIMEOUT}],
            become=True,
            profile='linux',
        )[0]
        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()
        if result.get('rc') != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='Apache Tomcat Dump 파일 점검 명령 실행에 실패했습니다.',
                stdout=stdout,
                stderr=stderr,
            )

        dump_files = [
            line.strip() for line in stdout.splitlines()
            if line.strip() and not line.strip().startswith('[')
        ]
        threshold = self.get_threshold_var('max_dump_count', default=0, value_type='int')
        metrics = {
            'dump_count': len(dump_files),
            'dump_files': dump_files,
        }
        thresholds = {'max_dump_count': threshold}
        if len(dump_files) > threshold:
            return self.warn(
                metrics=metrics,
                thresholds=thresholds,
                reasons='신규 Dump 파일이 기준보다 많이 발견되었습니다.',
                message='Apache Tomcat Dump 파일 경고: dump_count=%s, 기준=%s' % (
                    len(dump_files),
                    threshold,
                ),
            )
        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='신규 Dump 파일이 기준 이내입니다.',
            message='Apache Tomcat Dump 파일 정상: dump_count=%s, 기준=%s' % (
                len(dump_files),
                threshold,
            ),
        )


CHECK_CLASS = Check
