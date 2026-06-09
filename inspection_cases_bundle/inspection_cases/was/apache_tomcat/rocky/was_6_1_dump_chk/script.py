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
