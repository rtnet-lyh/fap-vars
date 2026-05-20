# -*- coding: utf-8 -*-

from .common._base import BaseCheck


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'linux'
    PARAMIKO_REUSE_SESSION = False

    DEFAULT_ERROR_LOG_PATH = '/home/exTMS/tmax/webtob/log/main'
    DEFAULT_WARNING_STATUS_CODE = 500
    COMMAND_TIMEOUT = 10

    def _build_command(self, error_log_path, status_code):
        path = error_log_path.rstrip('/')
        return 'grep "%s" $(ls %s/error.log*|sort|tail -n 1)' % (status_code, path)

    def run(self):
        error_log_path = self.get_host_var(key='error_log_path')

        if not error_log_path:
            error_log_path = self.get_threshold_var(
                'error_log_path', 
                default=self.DEFAULT_ERROR_LOG_PATH, 
                value_type='str'
            ).strip() or self.DEFAULT_ERROR_LOG_PATH

        status_code = self.get_threshold_var(
            'warning_status_code',
            default=self.DEFAULT_WARNING_STATUS_CODE,
            value_type='int',
        )
        command = self._build_command(error_log_path, status_code)

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
                message='WebtoB error log에서 500 상태를 확인하지 못했습니다.',
                stdout=stdout,
                stderr=stderr,
            )

        matches = [line.strip() for line in stdout.splitlines() if str(status_code) in line]
        metrics = {
            'error_log_path': error_log_path,
            'warning_status_code': status_code,
            'matching_status_count': len(matches),
            'sample_lines': matches[:20],
        }
        thresholds = {
            'error_log_path': error_log_path,
            'warning_status_code': status_code,
        }

        if matches:
            return self.warn(
                metrics=metrics,
                thresholds=thresholds,
                reasons='error log에서 HTTP 500 관련 로그가 발견되었습니다.',
                message='WebtoB 500 상태 경고: count=%s' % len(matches),
            )

        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='error log에서 HTTP 500 관련 로그가 발견되지 않았습니다.',
            message='WebtoB 500 상태 정상: status=%s 미검출' % status_code,
        )


CHECK_CLASS = Check
