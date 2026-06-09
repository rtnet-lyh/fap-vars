# -*- coding: utf-8 -*-

from .common._base import BaseCheck


COMMAND = "netstat -ntp | grep -E '8080|8009' | awk '{print $6}' | sort | uniq -c"
COMMAND_TIMEOUT = 20


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'linux'
    PARAMIKO_REUSE_SESSION = False

    def _parse_state_counts(self, stdout):
        counts = {}
        for line in stdout.splitlines():
            parts = line.strip().split()
            if len(parts) != 2:
                continue
            try:
                count = int(parts[0])
            except ValueError:
                continue
            counts[parts[1].upper()] = count
        return counts

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
                message='Apache Tomcat Connection Pool 연결 상태 점검 명령 실행에 실패했습니다.',
                stdout=stdout,
                stderr=stderr,
            )

        state_counts = self._parse_state_counts(stdout)
        threshold = self.get_threshold_var('max_established_conn', default=1000, value_type='int')
        established_count = state_counts.get('ESTABLISHED', 0)
        close_wait_count = state_counts.get('CLOSE_WAIT', 0)
        metrics = {
            'state_counts': state_counts,
            'established_count': established_count,
            'close_wait_count': close_wait_count,
        }
        thresholds = {'max_established_conn': threshold, 'max_close_wait_count': 0}
        if established_count > threshold or close_wait_count > 0:
            return self.warn(
                metrics=metrics,
                thresholds=thresholds,
                reasons='연결 수가 기준을 초과했거나 CLOSE_WAIT 상태가 확인되었습니다.',
                message='Apache Tomcat Connection Pool 경고: ESTABLISHED=%s, CLOSE_WAIT=%s, 기준=%s' % (
                    established_count,
                    close_wait_count,
                    threshold,
                ),
            )
        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='활성 연결 수와 CLOSE_WAIT 상태가 기준 이내입니다.',
            message='Apache Tomcat Connection Pool 정상: ESTABLISHED=%s, 기준=%s' % (
                established_count,
                threshold,
            ),
        )


CHECK_CLASS = Check
