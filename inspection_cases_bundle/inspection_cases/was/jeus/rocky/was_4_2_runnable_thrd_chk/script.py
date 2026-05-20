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
