# -*- coding: utf-8 -*-

from .common._base import BaseCheck


COMMAND = 'grep -i "{bad_word}" "$(ls -t {admin_log_path}/*.log | head -1)"'

class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'linux'
    PARAMIKO_REUSE_SESSION = False

    COMMAND_TIMEOUT = 20

    def _run_jeus_command(self, bad_word: str, admin_log_path: str):
        command = COMMAND.format(bad_word=bad_word,admin_log_path=admin_log_path)
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
        bad_word = self.get_threshold_var(key='bad_word', default='connection leak', value_type='str')
        admin_log_path = self.get_threshold_var(key='admin_log_path', default='/home/exTMS/tmax/jeus/log/adminServer', value_type='str')
        expected_matching_line_count = self.get_threshold_var(key='expected_matching_line_count', default=0, value_type='int')

        stdout, _stderr, error = self._run_jeus_command(bad_word, admin_log_path)
        if error:
            return error
        lines = [line.strip() for line in stdout.splitlines() if line.strip()]
        metrics = {'finding_label': bad_word, 'matching_line_count': len(lines), 'sample_lines': lines[:20]}
        thresholds = {'expected_matching_line_count': expected_matching_line_count}
        
        if lines:
            return self.warn(metrics=metrics, thresholds=thresholds, reasons='%s이 발견되었습니다.' % bad_word, message='JEUS 로그 패턴 경고: %s count=%s' % (bad_word, len(lines)))
        return self.ok(metrics=metrics, thresholds=thresholds, reasons='%s이 발견되지 않았습니다.' % bad_word, message='JEUS 로그 패턴 정상: %s 미검출' % bad_word)


CHECK_CLASS = Check
