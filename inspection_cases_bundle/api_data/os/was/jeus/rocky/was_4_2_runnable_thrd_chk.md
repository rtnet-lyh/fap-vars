# type_name

일상점검

# area_name

was

# category_name

상태점검

# application_type

jeus

# application

rocky

# inspection_code


WAS-JEUS-RKY-012

# is_required

필수

# inspection_name

장기수행 작업 확인

# inspection_content

오랜시간 동안 적체 중인 Thread 존재 유무 확인(스레드 여유 공간 확보를 위해 Tranjaction의 비정상적인 종료, DB Table 오류 등으로 인한 비정상적으로 장시간 적체 중인 스레드를 확인)

# inspection_command

```bash
for pid in $(ps -ef | grep "jeus.server.ServerBootstrapper" | grep -v grep | awk '{print $2}'); do echo "======== PID: $pid ========"; jstack 1559740 | awk '/^"/{t=$0} /Thread.State: RUNNABLE/{print t "\n" $0 "\n"}'; done;
```

# inspection_output

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

# description

- Thread State ("RUNNABLE"): 스레드가 CPU에서 실행 중인 상태를 나타내며, RUNNABLE 상태에서 오랫동안 유지되면 작업이 정상적으로 종료되지 않았을 가능성이 있음. 대부분의 스레드는 일정 시간 내에 종료되어야 하며, 스레드가 지나치게 오래 RUNNABLE 상태에 있으면 스레드 풀 설정을 조정하거나 작업 성능을 최적화하는 것이 필요. 
- Execution Time: 스레드가 특정 작업을 수행하는 데 걸리는 시간을 통해 실행 시간이 비정상적으로 길어지면 애플리케이션 성능에 악영향을 미칠 수 있으므로 성능 분석을 통해 작업을 최적화하고, 필요 시 작업을 분할하거나 스레드 수를 조정하는 것이 필요.

- **양호**: 출력된 스레드명의 개수가 `max_runnable_thread_pool`를 초과하지 않고 WAITING/BLOCKED 상태의 스레드가 적은 상태
- **경고**: 출력된 스레드명의 개수가 `max_runnable_thread_pool`를 초과하거나 WAITING/BLOCKED 상태의 스레드가 많은 상태
- **확인 필요**: 출력이 없거나 jstack 수행 불가 및 실행불가(권한/미설치 등)로 점검 불가한 상태

# thresholds

[
    {id: null, key: "max_runnable_thread_pool", value: "10", sortOrder: 0}
]

# inspection_script

# -*- coding: utf-8 -*-

from .common._base import BaseCheck


# COMMAND = 'for pid in $(ps -ef | grep "jeus.server.ServerBootstrapper" | grep -v grep | awk \'{print $2}\'); do echo "======== PID: $pid ========"; jstack $pid | awk \'/^"/{t=$0} /Thread.State: RUNNABLE/{print t "\\n" $0 "\\n"}\'; done'
COMMAND = 'for pid in $(ps -ef | grep "jeus.server.ServerBootstrapper" | grep -v grep | awk \'{print $2}\'); do echo "======== PID: $pid ========"; jstack $pid | grep -A 5 "RUNNABLE"; done;'

class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'linux'
    PARAMIKO_REUSE_SESSION = False

    COMMAND_TIMEOUT = 20

    def _run_jeus_command(self):
        result = self._run_paramiko_commands(
            [{'command': COMMAND, 'timeout': self.COMMAND_TIMEOUT}],
            become=True,
            profile='linux',
        )[0]
        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()
        if result.get('rc') != 0:
            return stdout, stderr, self.fail(
                '점검 명령 실행 실패',
                message='JEUS 점검 명령 실행에 실패했습니다.',
                stdout=stdout,
                stderr=stderr,
            )
        return stdout, stderr, None

    def run(self):
        stdout, _stderr, error = self._run_jeus_command()
        count_keyword = self.get_threshold_var(key='count_keyword', default='LongRunningTask.run', value_type='str')
        if error:
            return error
        long_running_count = stdout.count(count_keyword)
        threshold = self.get_threshold_var('max_long_running_count', default=10, value_type='int')
        metrics = {'long_running_count': long_running_count}
        thresholds = {'max_long_running_count': threshold}
        if long_running_count > threshold:
            return self.warn(metrics=metrics, thresholds=thresholds, reasons='RUNNABLE 스레드 수가 기준을 초과했습니다.', message='RUNNABLE Thread 경고: count=%s, 기준=%s' % (long_running_count, threshold))
        return self.ok(metrics=metrics, thresholds=thresholds, reasons='RUNNABLE 스레드 수가 기준 이하입니다.', message='RUNNABLE Thread 정상: count=%s, 기준=%s' % (long_running_count, threshold))


CHECK_CLASS = Check
