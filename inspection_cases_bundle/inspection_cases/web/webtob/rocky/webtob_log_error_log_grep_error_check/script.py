# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'linux'
    PARAMIKO_REUSE_SESSION = False

    DEFAULT_ERROR_LOG_PATH = '/home/exTMS/tmax/webtob/log/main'
    DEFAULT_CRITICAL_PATTERNS = 'CRITICAL|FATAL'
    COMMAND_TIMEOUT = 10

    def _build_command(self, error_log_path):
        path = error_log_path.rstrip('/')
        return 'grep -Ei "CRITICAL|FATAL|ERR-|error" $(ls %s/error.log*|sort|tail -n 1) | tail -20' % path

    def run(self):
        error_log_path = self.get_host_var(key='error_log_path')

        if not error_log_path:
            error_log_path = self.get_threshold_var(
                'error_log_path', 
                default=self.DEFAULT_ERROR_LOG_PATH, 
                value_type='str'
            ).strip() or self.DEFAULT_ERROR_LOG_PATH

        critical_patterns = self.get_threshold_var(
                'critical_patterns',
                default=self.DEFAULT_CRITICAL_PATTERNS,
                value_type='str',
        ).strip()
        
        command = self._build_command(error_log_path)

        result = self._run_paramiko_commands(
            [{'command': command, 'timeout': self.COMMAND_TIMEOUT}],
            become=True,
            profile='linux',
        )[0]

        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()
        if result.get('rc') != 0:
            return self.fail(
                'error log 명령 실행 실패',
                message='WebtoB error log를 확인하지 못했습니다.',
                stdout=stdout,
                stderr=stderr,
            )

        lines = [line.strip() for line in stdout.splitlines() if line.strip()]
        pattern = re.compile(critical_patterns, re.IGNORECASE)
        critical_lines = [line for line in lines if pattern.search(line)]
        metrics = {
            'error_log_path': error_log_path,
            'inspected_line_count': len(lines),
            'critical_fatal_count': len(critical_lines),
            'critical_fatal_lines': critical_lines[:20],
            'sample_lines': lines[:20],
        }
        thresholds = {
            'error_log_path': error_log_path,
            'critical_patterns': critical_patterns,
        }

        if critical_lines:
            return self.warn(
                metrics=metrics,
                thresholds=thresholds,
                reasons='error log에서 CRITICAL 또는 FATAL 로그가 발견되었습니다.',
                message='WebtoB error log 경고: critical_fatal_count=%s' % len(critical_lines),
            )

        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='error log에서 CRITICAL/FATAL 로그가 발견되지 않았습니다.',
            message='WebtoB error log 정상: inspected_line_count=%s, critical_fatal_count=0' % len(lines),
        )


CHECK_CLASS = Check
