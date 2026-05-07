# -*- coding: utf-8 -*-

from .common._base import BaseCheck


LOG_COMMAND = "dmesg | grep -i 'error|fail|warning'"


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_AUTH_TIMEOUT_SEC = 30

    def _is_become_enabled(self):
        value = self.get_connection_value('become', default=False)
        return str(value).strip().lower() in ('1', 'true', 'y', 'yes', 'on')

    def _build_become_command(self):
        method = str(self.get_connection_value('become_method', default='su -') or 'su -')
        method = ' '.join(method.strip().lower().split())
        user = str(self.get_connection_value('become_user', default='root') or 'root').strip() or 'root'

        if method == 'su':
            return 'su ' + user
        if method == 'su -':
            return 'su - ' + user
        if method == 'sudo':
            return 'sudo -u ' + user + ' -i'
        raise ValueError(f'unsupported become_method: {method}')

    def _build_paramiko_commands(self, command):
        if not self._is_become_enabled():
            return [command]

        return [
            {
                'command': self._build_become_command(),
                'timeout': 1,
                'ignore_prompt': True,
            },
            {
                'command': str(self.get_connection_value('become_password', default='') or ''),
                'hide_command': True,
            },
            command,
        ]

    def _run_check_command(self, command):
        try:
            results = self._run_paramiko_commands(self._build_paramiko_commands(command))
        except ValueError as exc:
            return 1, '', str(exc)

        for item in reversed(results):
            if item.get('command') == command:
                return item.get('rc'), item.get('stdout', ''), item.get('stderr', '')

        failed_result = next((item for item in results if item.get('rc') != 0), None)
        if failed_result:
            return failed_result.get('rc'), failed_result.get('stdout', ''), failed_result.get('stderr', '')
        return 1, '', 'paramiko command result not found'


    def _build_log_summary(self, lines, limit=3):
        if not lines:
            return '이상 로그 없음'

        summary_lines = [line.strip() for line in lines[:limit]]
        if len(lines) > limit:
            summary_lines.append(f'외 {len(lines) - limit}건')
        return ' | '.join(summary_lines)

    def run(self):
        failure_keywords_raw = self.get_threshold_var('failure_keywords', default='', value_type='str')

        rc, out, err = self._run_check_command(LOG_COMMAND)
        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'SSH 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )
        if rc not in (0, 1):
            return self.fail(
                '점검 명령 실행 실패',
                message=(
                    'Solaris 시스템 로그 점검에 실패했습니다. '
                    "현재 상태: dmesg | grep -i 'error|fail|warning' 명령을 정상적으로 실행하지 못했습니다."
                ),
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        text = (out or '').strip()
        stderr_text = (err or '').strip()
        failure_keywords = [keyword.strip() for keyword in failure_keywords_raw.split(',') if keyword.strip()]
        combined_text = '\n'.join([value for value in (text, stderr_text) if value])
        matched_failure_keywords = [keyword for keyword in failure_keywords if keyword.lower() in combined_text.lower()]
        if matched_failure_keywords:
            return self.fail(
                '시스템 로그 실패 키워드 감지',
                message=(
                    'Solaris 시스템 로그 점검에 실패했습니다. '
                    f'현재 상태: 출력에서 실패 키워드 {matched_failure_keywords}가 확인되었습니다.'
                ),
                stdout=text,
                stderr=stderr_text,
            )
        if stderr_text:
            return self.fail(
                '점검 명령 실행 실패',
                message=(
                    'Solaris 시스템 로그 점검에 실패했습니다. '
                    f'현재 상태: stderr 출력이 확인되었습니다: {stderr_text}'
                ),
                stdout=text,
                stderr=stderr_text,
            )

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if lines:
            return self.fail(
                '시스템 로그 이상 감지',
                message=(
                    'Solaris 시스템 로그 점검에 실패했습니다. '
                    f'현재 상태: error/fail/warning 패턴 로그 {len(lines)}건이 확인되었습니다. '
                    f'첫 로그: {lines[0]}. 로그 요약: {self._build_log_summary(lines)}.'
                ),
                stdout=text,
                stderr=stderr_text,
            )

        return self.ok(
            metrics={
                'matched_log_count': len(lines),
                'matched_logs': lines,
                'matched_failure_keywords': matched_failure_keywords,
            },
            thresholds={
                'failure_keywords': failure_keywords,
            },
            reasons='error, fail, warning 패턴의 시스템 로그가 검출되지 않았고 stderr도 없습니다.',
            message='Solaris 시스템 로그가 정상입니다. 현재 상태: error/fail/warning 패턴 로그 0건, stderr 0건으로 집계되었습니다.',
        )


CHECK_CLASS = Check
