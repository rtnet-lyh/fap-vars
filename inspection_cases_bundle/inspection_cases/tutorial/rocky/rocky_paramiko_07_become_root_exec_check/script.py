# -*- coding: utf-8 -*-

from .common._base import BaseCheck


ROOT_ACCESS_MARKER = 'PARAMIKO_ROOT_ACCESS_OK'
ROOT_CHECK_COMMAND = 'whoami; id -u; test -r /etc/shadow && echo ' + ROOT_ACCESS_MARKER


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'linux'
    PARAMIKO_AUTH_METHOD = 'password'
    PARAMIKO_TIMEOUT_SEC = 10

    def _is_become_enabled(self):
        value = self.get_application_credential_value('become', default=False)
        return str(value).strip().lower() in ('1', 'true', 'y', 'yes', 'on')

    def _become_command(self):
        method = str(self.get_application_credential_value('become_method', default='su -') or 'su -')
        method = ' '.join(method.strip().lower().split())
        user = str(self.get_application_credential_value('become_user', default='root') or 'root').strip() or 'root'

        if method == 'su':
            return 'su ' + user
        if method == 'su -':
            return 'su - ' + user
        raise ValueError(f'unsupported become_method: {method}')

    def _build_commands(self):
        if not self._is_become_enabled():
            return [ROOT_CHECK_COMMAND]

        password = str(self.get_application_credential_value('become_password', default='') or '')
        return [
            {
                'command': self._become_command(),
                'timeout': 1,
                'ignore_prompt': True,
            },
            {
                'command': password,
                'hide_command': True,
            },
            ROOT_CHECK_COMMAND,
        ]

    def _find_root_check_result(self, results):
        for item in reversed(results):
            if item.get('command') == ROOT_CHECK_COMMAND:
                return item
        return None

    def run(self):
        try:
            commands = self._build_commands()
        except ValueError as exc:
            return self.fail('권한 상승 설정 오류', message=str(exc))

        results = self._run_paramiko_commands(commands)
        failed = [
            item for item in results
            if item.get('rc') != 0 and not (item.get('command') == self._become_command() and item.get('timed_out'))
        ]
        if failed:
            first = failed[0]
            return self.fail(
                '점검 명령 실행 실패',
                message='Paramiko root 권한 확인 명령 실행에 실패했습니다.',
                stdout=(first.get('stdout') or '').strip(),
                stderr=(first.get('stderr') or '').strip(),
            )

        root_result = self._find_root_check_result(results)
        if not root_result:
            return self.fail(
                '점검 결과 없음',
                message='root 권한 확인 명령 결과가 없습니다.',
            )

        lines = [line.strip() for line in (root_result.get('stdout') or '').splitlines() if line.strip()]
        if len(lines) < 3:
            return self.fail(
                '출력 파싱 실패',
                message='whoami, id -u, root 접근 marker를 모두 확인하지 못했습니다.',
                stdout=(root_result.get('stdout') or '').strip(),
                stderr=(root_result.get('stderr') or '').strip(),
            )

        expected_user = str(
            self.get_application_credential_value('become_user', default='root') or 'root'
        ).strip() or 'root'
        actual_user = lines[0]
        actual_uid = lines[1]
        root_access_ok = ROOT_ACCESS_MARKER in lines

        if actual_user != expected_user or actual_uid != '0' or not root_access_ok:
            return self.fail(
                'root 권한 확인 실패',
                message=(
                    f'expected_user={expected_user}, actual_user={actual_user}, '
                    f'uid={actual_uid}, marker={root_access_ok}'
                ),
                stdout=(root_result.get('stdout') or '').strip(),
                stderr=(root_result.get('stderr') or '').strip(),
            )

        return self.ok(
            metrics={
                'connection_method': 'paramiko',
                'become_enabled': self._is_become_enabled(),
                'become_method': str(self.get_application_credential_value('become_method', default='su -') or 'su -'),
                'become_user': expected_user,
                'root_identity': actual_user,
                'root_uid': actual_uid,
                'root_access_marker': root_access_ok,
            },
            thresholds={},
            reasons='Paramiko 상호작용 입력으로 root 권한상승과 root 전용 파일 접근을 정상 확인했습니다.',
            message=f'Paramiko root 권한상승 예제가 정상 수행되었습니다. user={actual_user}, uid={actual_uid}',
        )


CHECK_CLASS = Check
