# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


COMMAND = 'tail -n 100 /home/koem01/apache-tomcat-8.0.32/logs/catalina.out'
COMMAND_TIMEOUT = 20
CHECK_NAME = '클라이언트 접속 로그'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'linux'
    PARAMIKO_REUSE_SESSION = False

    def _warning_words(self):
        raw_words = self.get_threshold_var(
            'warning_words',
            default='ERROR,WARN,FATAL,CRITICAL,EXCEPTION,SEVERE,HTTP 4,HTTP 5, 400 , 500 ',
            value_type='str',
        )
        return [word.strip().upper() for word in re.split(r'[,|]+', raw_words) if word.strip()]

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
                message='Apache Tomcat 로그 점검 명령 실행에 실패했습니다.',
                stdout=stdout,
                stderr=stderr,
            )

        lines = [line.strip() for line in stdout.splitlines() if line.strip()]
        if not lines:
            return self.fail('로그 출력 없음', message='로그 출력이 비어 있습니다.', stdout=stdout)

        warning_words = self._warning_words()
        warning_lines = [
            line for line in lines
            if any(word in line.upper() for word in warning_words)
        ]
        threshold = self.get_threshold_var('max_error_count', default=0, value_type='int')
        metrics = {
            'inspected_line_count': len(lines),
            'error_count': len(warning_lines),
            'warning_lines': warning_lines[:20],
            'sample_lines': lines[:20],
        }
        thresholds = {
            'max_error_count': threshold,
            'warning_patterns': '|'.join(warning_words),
        }
        if len(warning_lines) > threshold:
            return self.warn(
                metrics=metrics,
                thresholds=thresholds,
                reasons='로그에서 클라이언트 접속 이상 패턴이 발견되었습니다.',
                message='Apache Tomcat %s 점검 경고: error_count=%s, 기준=%s' % (
                    CHECK_NAME,
                    len(warning_lines),
                    threshold,
                ),
            )
        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='로그에서 클라이언트 접속 이상 패턴이 발견되지 않았습니다.',
            message='Apache Tomcat %s 점검 정상: inspected_line_count=%s' % (
                CHECK_NAME,
                len(lines),
            ),
        )


CHECK_CLASS = Check
