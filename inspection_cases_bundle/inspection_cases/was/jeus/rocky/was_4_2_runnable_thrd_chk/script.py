# -*- coding: utf-8 -*-

from .common._base import BaseCheck


COMMAND = 'for pid in $(ps -ef | grep "jeus.server.ServerBootstrapper" | grep -v grep | awk \'{print $2}\'); do echo "======== PID: $pid ========"; jstack $pid | awk \'/^"/{t=$0} /Thread.State: RUNNABLE/{print t "\\n" $0 "\\n"}\'; done'


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
        if error:
            return error
        runnable_count = stdout.count('Thread.State: RUNNABLE')
        threshold = self.get_threshold_var('max_runnable_thread_pool', default=10, value_type='int')
        metrics = {'runnable_thread_count': runnable_count}
        thresholds = {'max_runnable_thread_pool': threshold}
        if runnable_count > threshold:
            return self.warn(metrics=metrics, thresholds=thresholds, reasons='RUNNABLE 스레드 수가 기준을 초과했습니다.', message='RUNNABLE Thread 경고: count=%s, 기준=%s' % (runnable_count, threshold))
        return self.ok(metrics=metrics, thresholds=thresholds, reasons='RUNNABLE 스레드 수가 기준 이하입니다.', message='RUNNABLE Thread 정상: count=%s, 기준=%s' % (runnable_count, threshold))


CHECK_CLASS = Check
