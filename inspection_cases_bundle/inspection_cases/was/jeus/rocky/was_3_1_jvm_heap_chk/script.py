# -*- coding: utf-8 -*-

from .common._base import BaseCheck


COMMAND = 'for pid in $(ps -ef | grep "jeus.server.ServerBootstrapper" | grep -v grep | awk \'{print $2}\'); do echo "======== PID: $pid ========"; jmap -heap $pid; echo; done'


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
        heap_sizes = []
        for line in stdout.splitlines():
            if 'MaxHeapSize' not in line or '(' not in line:
                continue
            try:
                heap_sizes.append(float(line.split('(')[1].split('MB')[0]))
            except (IndexError, ValueError):
                continue
        if not heap_sizes:
            return self.fail('Heap 크기 파싱 실패', message='jmap 출력에서 MaxHeapSize 값을 확인하지 못했습니다.', stdout=stdout)
        threshold = self.get_threshold_var('max_heap_size', default=8192.0, value_type='float')
        max_heap_size = max(heap_sizes)
        metrics = {'jvm_count': len(heap_sizes), 'max_heap_size_mb': max_heap_size, 'heap_sizes_mb': heap_sizes}
        thresholds = {'max_heap_size': threshold}
        if max_heap_size > threshold:
            return self.warn(metrics=metrics, thresholds=thresholds, reasons='MaxHeapSize가 기준을 초과했습니다.', message='JEUS JVM Heap 경고: 최대 %.1fMB, 기준 %.1fMB' % (max_heap_size, threshold))
        return self.ok(metrics=metrics, thresholds=thresholds, reasons='MaxHeapSize가 기준 이하입니다.', message='JEUS JVM Heap 정상: 최대 %.1fMB, 기준 %.1fMB' % (max_heap_size, threshold))


CHECK_CLASS = Check
