# -*- coding: utf-8 -*-

from .common._base import BaseCheck

COMMAND = 'grep -i "{search_keyword}" "$(ls -t {jeus_log_path}/*.log | head -1)"'

class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'linux'
    PARAMIKO_REUSE_SESSION = False

    COMMAND_TIMEOUT = 20

    def _run_jeus_command(self, search_keyword, jeus_log_path):    
        command = COMMAND.format(search_keyword=search_keyword, jeus_log_path=jeus_log_path)    

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
        search_keyword = self.get_threshold_var(
            key='search_keyword', 
            default='connection pool exhausted',
            value_type='str',
        )
        
        jeus_log_path = self.get_threshold_var(
            key='jeus_log_path', 
            default='/home/exTMS/tmax/jeus/log/extms1',
            value_type='str',
        )

        stdout, _stderr, error = self._run_jeus_command(search_keyword, jeus_log_path)
        if error:
            return error
        lines = [line.strip() for line in stdout.splitlines() if line.strip()]
        threshold = self.get_threshold_var('max_message_count', default=0, value_type='int')
        metrics = {'message_count': len(lines), 'sample_lines': lines[:20]}
        thresholds = {'max_message_count': threshold}
        if len(lines) > threshold:
            return self.warn(metrics=metrics, thresholds=thresholds, reasons=f'{search_keyword} 메시지 수가 기준을 초과했습니다.', message='%s 메시지 경고: count=%s, 기준=%s' % (search_keyword, len(lines), threshold))
        return self.ok(metrics=metrics, thresholds=thresholds, reasons=f'{search_keyword} 메시지 수가 기준 이하입니다.', message='%s 메시지 정상: count=%s, 기준=%s' % (search_keyword, len(lines), threshold))


CHECK_CLASS = Check
