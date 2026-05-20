# -*- coding: utf-8 -*-

from .common._base import BaseCheck


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'linux'
    PARAMIKO_REUSE_SESSION = False

    DEFAULT_ACCESS_LOG_PATH = '/home/exTMS/tmax/webtob/log/main'
    DEFAULT_WARNING_STATUS_CODE = 404
    COMMAND_TIMEOUT = 10

    def _build_command(self, access_log_path, status_code):
        path = access_log_path.rstrip('/')
        return "awk '$(NF-2)==%s' $(ls %s/access.log*|sort|tail -n 1) | tail -20" % (
            status_code,
            path,
        )

    def _parse_status_lines(self, stdout, status_code):
        matches = []
        for line in str(stdout or '').splitlines():
            parts = line.split()
            if len(parts) < 3:
                continue
            if parts[-3] == str(status_code):
                matches.append(line.strip())
        return matches

    def run(self):
        access_log_path = self.get_host_var(key='access_log_path')

        if not access_log_path:
            access_log_path = self.get_threshold_var(
                'access_log_path', 
                default=self.DEFAULT_ACCESS_LOG_PATH, 
                value_type='str'
            ).strip()

        status_code = self.get_threshold_var(
            'warning_status_code',
            default=self.DEFAULT_WARNING_STATUS_CODE,
            value_type='int',
        )

        command = self._build_command(access_log_path, status_code)

        result = self._run_paramiko_commands(
            [{'command': command, 'timeout': self.COMMAND_TIMEOUT}],
            become=True,
            profile='linux',
        )[0]

        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()
        
        if result.get('rc') != 0:
            return self.fail(
                'access log 명령 실행 실패',
                message='WebtoB access log에서 404 응답을 확인하지 못했습니다.',
                stdout=stdout,
                stderr=stderr,
            )

        matches = self._parse_status_lines(stdout, status_code)
        metrics = {
            'access_log_path': access_log_path,
            'warning_status_code': status_code,
            'matching_status_count': len(matches),
            'sample_lines': matches[:20],
        }
        thresholds = {
            'access_log_path': access_log_path,
            'warning_status_code': status_code,
        }

        if matches:
            return self.warn(
                metrics=metrics,
                thresholds=thresholds,
                reasons='최신 access log에서 HTTP 404 응답이 발견되었습니다.',
                message='WebtoB access log 404 응답 경고: count=%s' % len(matches),
            )

        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='최신 access log에서 HTTP 404 응답이 발견되지 않았습니다.',
            message='WebtoB access log 404 응답 정상: status=%s 미검출' % status_code,
        )


CHECK_CLASS = Check
