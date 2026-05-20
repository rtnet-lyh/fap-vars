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
