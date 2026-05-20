# -*- coding: utf-8 -*-

from .common._base import BaseCheck


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'linux'
    PARAMIKO_REUSE_SESSION = False

    DEFAULT_ACCESS_LOG_PATH = '/home/exTMS/tmax/webtob/log/main'
    DEFAULT_MAX_RESPONSE_TIME = 1000
    COMMAND_TIMEOUT = 10

    def _build_command(self, access_log_path, max_response_time):
        path = access_log_path.rstrip('/')
        return "awk '$NF >= %s' $(ls %s/access.log*|sort|tail -n 1) | head -20" % (
            max_response_time,
            path,
        )

    def _parse_response_times(self, stdout):
        rows = []
        for line in str(stdout or '').splitlines():
            parts = line.split()
            if not parts:
                continue
            try:
                response_time = int(float(parts[-1]))
            except ValueError:                
                continue
            rows.append({
                'response_time': response_time,
                'line': line.strip(),
            })
        return rows

    def run(self):
        access_log_path = self.get_host_vars(key='access_log_path')
        if not access_log_path:
            access_log_path = self.get_threshold_var(
                'access_log_path', 
                default=self.DEFAULT_ACCESS_LOG_PATH, 
                value_type='str'
            ).strip()

        max_response_time = self.get_threshold_var(
            'max_response_time',
            default=self.DEFAULT_MAX_RESPONSE_TIME,
            value_type='int',
        )

        command = self._build_command(access_log_path, max_response_time)

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
                message='WebtoB access log에서 응답시간을 확인하지 못했습니다.',
                stdout=stdout,
                stderr=stderr,
            )

        rows = self._parse_response_times(stdout)
        if stdout and not rows:
            return self.fail(
                '응답시간 파싱 실패',
                message='access log 출력에서 마지막 컬럼 응답시간을 확인하지 못했습니다.',
                stdout=stdout,
                stderr=stderr,
            )

        over_rows = [row for row in rows if row['response_time'] >= max_response_time]
        max_observed = max((row['response_time'] for row in rows), default=0)
        metrics = {
            'access_log_path': access_log_path,
            'max_response_time': max_response_time,
            'slow_response_count': len(over_rows),
            'max_observed_response_time': max_observed,
            'sample_lines': [row['line'] for row in over_rows[:20]],
        }
        thresholds = {
            'access_log_path': access_log_path,
            'max_response_time': max_response_time,
        }

        if over_rows:
            return self.warn(
                metrics=metrics,
                thresholds=thresholds,
                reasons='기준 이상의 응답시간이 발견되었습니다.',
                message='WebtoB 응답시간 경고: 최대 %sms, 기준 %sms' % (
                    max_observed,
                    max_response_time,
                ),
            )

        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='기준 이상의 응답시간이 발견되지 않았습니다.',
            message='WebtoB 응답시간 정상: 기준 %sms 이상 로그 없음' % max_response_time,
        )


CHECK_CLASS = Check
