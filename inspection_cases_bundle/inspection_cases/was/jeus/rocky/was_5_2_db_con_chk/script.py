# -*- coding: utf-8 -*-

from .common._base import BaseCheck
import re

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
            default='connection',
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
        if not lines:
            return self.ok(
                metrics={},
                thresholds={},
                reasons='DB Connection 로그 출력 없음',
                message='DB Connection 로그 출력 없음',                
            )
        
        abnormal_words = self.get_threshold_var(
            key='abnormal_words',
            default='TIMEOUT,CLOSED',
            value_type='str',
        )
        abnormal_words = re.split('[,|]+', abnormal_words)
        abnormal_words = set(abnormal_words)
        abnormal_lines = [line for line in lines if any(word in line.upper() for word in abnormal_words)]
        metrics = {
            'connection_log_count': len(lines), 
            'abnormal_line_count': len(abnormal_lines), 
            'abnormal_lines': abnormal_lines[:20], 
            'sample_lines': lines[:20]
        }
        thresholds = {'abnormal_patterns': '|'.join(abnormal_words)}

        if abnormal_lines:
            return self.warn(
                metrics=metrics, 
                thresholds=thresholds, 
                reasons='DB Connection 로그에서 이상 징후가 발견되었습니다.', 
                message='DB Connection 상태 경고: abnormal_line_count=%s' % len(abnormal_lines)
            )

        return self.ok(
            metrics=metrics, 
            thresholds=thresholds, 
            reasons='DB Connection 로그에서 이상 징후가 발견되지 않았습니다.', 
            message='DB Connection 상태 정상: connection_log_count=%s' % len(lines)
        )


CHECK_CLASS = Check
