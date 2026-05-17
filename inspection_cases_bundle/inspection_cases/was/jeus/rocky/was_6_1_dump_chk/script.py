# -*- coding: utf-8 -*-

from .common._base import BaseCheck


COMMAND = 'for pid in $(ps -ef | grep "jeus.server.ServerBootstrapper" | grep -v grep | awk \'{print $2}\'); do echo "======== PID: $pid ========"; jcmd $pid VM.flags; done'


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
        pid_count = stdout.count('======== PID:')
        has_heap_dump = '-XX:+HeapDumpOnOutOfMemoryError' in stdout
        has_heap_dump_path = '-XX:HeapDumpPath=' in stdout
        metrics = {'pid_count': pid_count, 'heap_dump_on_oom': has_heap_dump, 'heap_dump_path': has_heap_dump_path}
        thresholds = {'required_flags': ['-XX:+HeapDumpOnOutOfMemoryError', '-XX:HeapDumpPath=']}
        if pid_count == 0:
            return self.fail('JVM 옵션 출력 없음', message='jcmd VM.flags 출력이 비어 있습니다.', stdout=stdout)
        if not (has_heap_dump and has_heap_dump_path):
            return self.warn(metrics=metrics, thresholds=thresholds, reasons='HeapDump 옵션이 누락되었습니다.', message='JEUS Dump 옵션 경고: heap_dump_on_oom=%s, heap_dump_path=%s' % (has_heap_dump, has_heap_dump_path))
        return self.ok(metrics=metrics, thresholds=thresholds, reasons='HeapDump 옵션이 설정되어 있습니다.', message='JEUS Dump 옵션 정상: pid_count=%s' % pid_count)


CHECK_CLASS = Check
