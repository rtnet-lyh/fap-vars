# -*- coding: utf-8 -*-

from .common._base import BaseCheck


COMMAND = 'grep -i "Full GC" $(ls /home/exTMS/tmax/jeus/log/gclog/*gc.log*|sort|tail -n 1) | wc -l'


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
        try:
            full_gc_count = int(stdout.split()[0])
        except (IndexError, ValueError):
            return self.fail('Full GC 횟수 파싱 실패', message='Full GC 횟수 값을 확인하지 못했습니다.', stdout=stdout)
        threshold = self.get_threshold_var('max_frequency', default=2, value_type='int')
        metrics = {'full_gc_count': full_gc_count}
        thresholds = {'max_frequency': threshold}
        if full_gc_count > threshold:
            return self.warn(metrics=metrics, thresholds=thresholds, reasons='Full GC 발생 횟수가 기준을 초과했습니다.', message='Full GC 발생 빈도 경고: count=%s, 기준=%s' % (full_gc_count, threshold))
        return self.ok(metrics=metrics, thresholds=thresholds, reasons='Full GC 발생 횟수가 기준 이하입니다.', message='Full GC 발생 빈도 정상: count=%s, 기준=%s' % (full_gc_count, threshold))


CHECK_CLASS = Check
