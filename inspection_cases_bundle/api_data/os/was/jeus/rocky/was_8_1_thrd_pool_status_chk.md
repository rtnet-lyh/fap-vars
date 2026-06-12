# type_name

일상점검

# area_name

상태점검

# category_name

was

# application_type

jeus

# application

rocky

# inspection_code

WAS-JEUS-ROCKY-REPLAY-017

# is_required

권고

# inspection_name

평균처리시간 점검

# inspection_content

요청건수 및 전체 처리시간, 평균처리시간 확인(평균 처리 응답시간을 확인 하여 서비스 지연 처리 확인을 위한 점검)

# inspection_command

```bash
jeusadmin -u jeus -p jeus "show-thread-pool-status adminServer"
```

# inspection_output

```text

```

# description

- Active Threads: 현재 스레드 풀에서 요청을 처리 중인 스레드 수로, Active Threads가 Max Threads에 가까워지면 시스템이 과부하 상태로 성능 저하가 발생할 수 있음. 스레드 풀이 과도하게 활성화될 경우 스레드 풀 크기를 조정하거나 성능 최적화를 수행하는 것이 필요. 
- Idle Threads: 대기 중인 스레드 수로, 요청을 처리할 수 있는 여유 스레드의 수를 나타냄. Idle  Threads가 적으면 새로운 요청이 대기 상태에 들어가면서 처리 지연이 발생할 수 있으므로, 대기 스레드가 충분한지 확인하고 부족할 경우 스레드 풀 크기를 늘리거나 성능 최적화를 통해 대기 스레드를 확보하는 것이 필요. 
- Task Count: 현재 스레드 풀에서 처리 중인 전체 작업 수로, Task Count가 지나치게 높으면 
서비스의 처리 성능이 저하될 수 있음. 스레드 풀에서 처리할 수 있는 작업 수가 한계를 
넘어서면 시스템 성능에 영향을 미치므로, 처리 중인 작업 수가 많을 경우 성능 최적화 또는 스레드 풀 크기 확장이 필요. 
※ 이 정보를 통해 성능 저하나 서비스 지연 가능성을 간접적으로 파악할 수 있지만, JEUS에서 요청 처리 시간과 평균 처리 시간을 직접적으로 제공하는 명령어는 없음.

# thresholds

[
    {id: null, key: "max_active_threads", value: "20", sortOrder: 0}
,
{id: null, key: "max_idle_thread", value: "10", sortOrder: 1}
,
{id: null, key: "max_task_count", value: "2000", sortOrder: 2}
]

# inspection_script

# -*- coding: utf-8 -*-

from .common._base import BaseCheck


COMMAND = 'jeusadmin -u {user} -p {pw} show-thread-pool-status {pool_name}'
# cd /home/exTMS;source .bash_profile;jeusadmin -u jeus -p jeus show-thread-pool-status default
# cd {home_path};source .bash_profile;jeusadmin -u {user} -p {pw} show-thread-pool-status {pool_name}

class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'linux'
    PARAMIKO_REUSE_SESSION = False

    COMMAND_TIMEOUT = 20

    def _run_jeus_command(self, home_path, user, pw, pool_name):
        command = f"cd {home_path};source .bash_profile;{COMMAND.format(user=user, pw=pw, pool_name=pool_name)}" 

        result = self._run_paramiko_commands(
            [{'command': command, 'timeout': self.COMMAND_TIMEOUT}],
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

    def _parse_values(self, stdout):
        values = {}
        for line in stdout.splitlines():
            if ':' not in line:
                continue
            key, value = line.split(':', 1)
            if value.strip().isdigit():
                values[key.strip()] = int(value.strip())
        return values

    def run(self):
        home_path = self.get_threshold_var(key='home_path', default='/home/exTMS', value_type='str')
        user = self.get_threshold_var(key='user', default='jeus', value_type='str')
        pw = self.get_threshold_var(key='pw', default='jeus', value_type='str')
        pool_name = self.get_threshold_var(key='pool_name', default='default', value_type='str')

        stdout, _stderr, error = self._run_jeus_command(home_path, user, pw, pool_name)
        if error:
            return error
        values = self._parse_values(stdout)
        missing = [key for key in ('Active Threads', 'Idle Threads', 'Task Count') if key not in values]
        if missing:
            return self.fail('Thread Pool 상태 파싱 실패', message='Thread Pool 출력에서 값을 확인하지 못했습니다: %s' % ', '.join(missing), stdout=stdout)
        thresholds = {'max_active_threads': self.get_threshold_var('max_active_threads', default=20, value_type='int'), 'max_idle_thread': self.get_threshold_var('max_idle_thread', default=10, value_type='int'), 'max_task_count': self.get_threshold_var('max_task_count', default=2000, value_type='int')}
        failed = []
        if values['Active Threads'] > thresholds['max_active_threads']:
            failed.append('Active Threads')
        if values['Idle Threads'] > thresholds['max_idle_thread']:
            failed.append('Idle Threads')
        if values['Task Count'] > thresholds['max_task_count']:
            failed.append('Task Count')
        metrics = {'thread_pool_values': values, 'failed_checks': failed}
        if failed:
            return self.warn(metrics=metrics, thresholds=thresholds, reasons='Thread Pool 값이 기준을 초과했습니다.', message='JEUS Thread Pool 상태 경고: 기준 초과=%s' % ', '.join(failed))
        return self.ok(metrics=metrics, thresholds=thresholds, reasons='Thread Pool 값이 기준 이하입니다.', message='JEUS Thread Pool 상태 정상: Active=%s, Idle=%s, Task=%s' % (values['Active Threads'], values['Idle Threads'], values['Task Count']))


CHECK_CLASS = Check
