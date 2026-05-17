# -*- coding: utf-8 -*-

from .common._base import BaseCheck


COMMAND = "awk '$(NF-2) >= 400 && $(NF-2) <= 409 || $(NF-2) >=500 && $(NF-2) <= 509' $(ls /home/exTMS/tmax/jeus/log/adminServer/servlet/access.log*|sort|tail -n 1)"


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

    FINDING_LABEL = 'HTTP 400/500대 오류'

    def run(self):
        stdout, _stderr, error = self._run_jeus_command()
        if error:
            return error
        lines = [line.strip() for line in stdout.splitlines() if line.strip()]
        metrics = {'finding_label': self.FINDING_LABEL, 'matching_line_count': len(lines), 'sample_lines': lines[:20]}
        thresholds = {'expected_matching_line_count': 0}
        if lines:
            return self.warn(metrics=metrics, thresholds=thresholds, reasons='%s이 발견되었습니다.' % self.FINDING_LABEL, message='JEUS 로그 패턴 경고: %s count=%s' % (self.FINDING_LABEL, len(lines)))
        return self.ok(metrics=metrics, thresholds=thresholds, reasons='%s이 발견되지 않았습니다.' % self.FINDING_LABEL, message='JEUS 로그 패턴 정상: %s 미검출' % self.FINDING_LABEL)


CHECK_CLASS = Check
