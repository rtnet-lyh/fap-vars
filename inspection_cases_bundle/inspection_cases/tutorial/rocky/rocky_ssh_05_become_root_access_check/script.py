# -*- coding: utf-8 -*-

import shlex

from .common._base import BaseCheck


BECOME_USER_MARKER = '__BECOME_USER__:'
ROOT_ACCESS_COMMAND = 'whoami && ls /root >/dev/null && echo ROOT_DIR_ACCESS_OK'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def _is_become_enabled(self):
        become_raw = self.get_application_credential_value('become', default=False)
        return str(become_raw).strip().lower() == 'true'

    def _mask_command_history(self, *secrets):
        if not self._command_history:
            return
        masked_cmd = self._command_history[-1].get('cmd', '')
        for secret in secrets:
            if secret:
                masked_cmd = masked_cmd.replace(secret, '*****')
        self._command_history[-1]['cmd'] = masked_cmd

    def _build_command(self):
        if not self._is_become_enabled():
            return ROOT_ACCESS_COMMAND

        become_method = str(self.get_application_credential_value('become_method', default='su -') or 'su -').strip().lower()
        become_user = str(self.get_application_credential_value('become_user', default='root') or 'root').strip() or 'root'
        become_password = str(self.get_application_credential_value('become_password', default='') or '')
        normalized_become_method = ' '.join(become_method.split())

        if normalized_become_method not in ('su', 'su -'):
            raise ValueError(f'unsupported become_method: {become_method}')

        become_script = "current_user=$(whoami); echo {marker}${{current_user}}; {command}".format(
            marker=shlex.quote(BECOME_USER_MARKER),
            command=ROOT_ACCESS_COMMAND,
        )
        return "bash -lc " + shlex.quote(
            "printf '%s\\n' {password} | su - {user} -c {command}".format(
                password=shlex.quote(become_password),
                user=shlex.quote(become_user),
                command=shlex.quote("bash -lc " + shlex.quote(become_script)),
            )
        )

    def run(self):
        try:
            command = self._build_command()
        except ValueError as exc:
            return self.fail(
                '권한 상승 설정 오류',
                message=str(exc),
            )

        become_password = str(self.get_application_credential_value('become_password', default='') or '')
        expected_user = str(self.get_application_credential_value('become_user', default='root') or 'root').strip() or 'root'

        rc, out, err = self._ssh(command)
        self._mask_command_history(become_password)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'SSH 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='su - 권한 상승 예제 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        lines = [line.strip() for line in (out or '').splitlines() if line.strip()]
        if not lines:
            return self.fail(
                '출력 파싱 실패',
                message='권한 상승 예제 결과가 비어 있습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        actual_become_user = ''
        payload_lines = list(lines)
        if self._is_become_enabled():
            marker_line = next((line for line in lines if line.startswith(BECOME_USER_MARKER)), '')
            if not marker_line:
                return self.fail(
                    '권한 상승 사용자 확인 실패',
                    message='권한 상승 후 사용자 marker를 찾지 못했습니다.',
                    stdout=(out or '').strip(),
                    stderr=(err or '').strip(),
                )
            actual_become_user = marker_line.split(BECOME_USER_MARKER, 1)[1].strip()
            if actual_become_user != expected_user:
                return self.fail(
                    '권한 상승 사용자 불일치',
                    message=f'권한 상승 사용자가 기대값과 다릅니다: expected={expected_user}, actual={actual_become_user}',
                    stdout=(out or '').strip(),
                    stderr=(err or '').strip(),
                )
            payload_lines = [line for line in lines if not line.startswith(BECOME_USER_MARKER)]

        if not payload_lines or payload_lines[0] != expected_user:
            return self.fail(
                '권한 상승 사용자 출력 없음',
                message='whoami 결과에서 기대한 root 사용자를 확인하지 못했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        if 'ROOT_DIR_ACCESS_OK' not in payload_lines:
            return self.fail(
                'root 디렉터리 접근 확인 실패',
                message='권한 상승 후 /root 접근 확인 문자열을 찾지 못했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        return self.ok(
            metrics={
                'become_enabled': self._is_become_enabled(),
                'become_user': actual_become_user or expected_user,
                'root_identity': payload_lines[0],
                'root_dir_access': True,
            },
            thresholds={},
            reasons='su - 권한상승과 root 전용 경로 접근을 정상 확인했습니다.',
            message=f'_ssh + su - 예제가 정상 수행되었습니다. become_user={actual_become_user or expected_user}',
        )


CHECK_CLASS = Check
