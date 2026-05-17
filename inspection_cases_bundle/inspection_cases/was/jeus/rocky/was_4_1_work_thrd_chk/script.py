# -*- coding: utf-8 -*-

from .common._base import BaseCheck


COMMAND = 'for pid in $(ps -ef | grep "jeus.server.ServerBootstrapper" | grep -v grep | awk \'{print $2}\'); do echo "======== PID: $pid ========"; jstack $pid | awk \'/^"/ {thread=$0} /Thread.State/ {state=$0} /java.util.concurrent.ThreadPoolExecutor/ {print thread; print state; print $0; print ""}\'; done'


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
        thread_lines = [line for line in stdout.splitlines() if line.strip().startswith('"')]
        waiting_blocked_lines = [line.strip() for line in stdout.splitlines() if 'Thread.State: WAITING' in line or 'Thread.State: BLOCKED' in line]
        threshold = self.get_threshold_var('max_thread_pool', default=10, value_type='int')
        metrics = {'thread_pool_stack_count': len(thread_lines), 'waiting_blocked_count': len(waiting_blocked_lines), 'waiting_blocked_lines': waiting_blocked_lines[:20]}
        thresholds = {'max_thread_pool': threshold}
        if len(thread_lines) > threshold:
            return self.warn(metrics=metrics, thresholds=thresholds, reasons='Thread Pool 스레드 수가 기준을 초과했습니다.', message='Work Thread Pool 경고: thread_count=%s, 기준=%s' % (len(thread_lines), threshold))
        return self.ok(metrics=metrics, thresholds=thresholds, reasons='Thread Pool 스레드 수가 기준 이하입니다.', message='Work Thread Pool 정상: thread_count=%s, 기준=%s' % (len(thread_lines), threshold))


CHECK_CLASS = Check
