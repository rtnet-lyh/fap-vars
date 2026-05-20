# -*- coding: utf-8 -*-

from .common._base import BaseCheck
import re

# COMMAND = 'tail -n 50 /home/exTMS/tmax/jeus/log/adminServer/JeusServer.log'
COMMAND = 'tail -100 $(find -L {admin_log_path} -iname "{log_file}" | xargs ls -t | head -1)'

class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'linux'
    PARAMIKO_REUSE_SESSION = False

    COMMAND_TIMEOUT = 20

    def _run_jeus_command(self):
        admin_log_path = self.get_threshold_var(
            key='admin_log_path',
            default='/home/exTMS/tmax/jeus/log',
            value_type='str',
        )

        log_file = self.get_threshold_var(
            key='log_file',
            default='JeusServer.log',
            value_type='str',
        )

        command = COMMAND.format(admin_log_path=admin_log_path, log_file=log_file)

        result = self._run_paramiko_commands(
            [{'command': command, 'timeout': self.COMMAND_TIMEOUT}],
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
        lines = [line.strip() for line in stdout.splitlines() if line.strip()]
        if not lines:
            return self.fail('로그 출력 없음', message='로그 출력이 비어 있습니다.', stdout=stdout)
        
        warning_words = self.get_threshold_var(
            key='warning_words', 
            default='ERROR,WARN,FATAL,CRITICAL,EXCEPTION', 
            value_type='str'
        )
        warning_words = re.split(r'[,|]+', warning_words)
        
        warning_lines = [line for line in lines if any(word in line.upper() for word in warning_words)]
        metrics = {'inspected_line_count': len(lines), 'warning_line_count': len(warning_lines), 'warning_lines': warning_lines[:20], 'sample_lines': lines[:20]}
        thresholds = {'warning_patterns': '|'.join(warning_words)}

        if warning_lines:
            return self.warn(metrics=metrics, thresholds=thresholds, reasons='로그에서 ERROR/WARN 계열 라인이 발견되었습니다.', message='JEUS 로그 점검 경고: warning_line_count=%s' % len(warning_lines))
        return self.ok(metrics=metrics, thresholds=thresholds, reasons='로그에서 ERROR/WARN 계열 라인이 발견되지 않았습니다.', message='JEUS 로그 점검 정상: inspected_line_count=%s' % len(lines))


CHECK_CLASS = Check
