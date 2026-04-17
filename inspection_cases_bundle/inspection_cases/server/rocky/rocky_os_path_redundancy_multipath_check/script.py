# -*- coding: utf-8 -*-

import re
import shlex

from .common._base import BaseCheck


MULTIPATH_COMMAND = 'multipath -ll'
BECOME_USER_MARKER = '__BECOME_USER__:'
ABNORMAL_MARKERS = ('failed', 'faulty', 'offline')
GROUP_STATUS_PATTERN = re.compile(r'status=(\w+)', re.IGNORECASE)
PATH_LINE_PATTERN = re.compile(r'(\d+:\d+:\d+:\d+)\s+(\S+)\s+\d+:\d+\s+(.+)$')


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
        become_method = str(self.get_application_credential_value('become_method', default='') or '').strip().lower()
        become_user = str(self.get_application_credential_value('become_user', default='root') or 'root').strip() or 'root'
        become_password = str(self.get_application_credential_value('become_password', default='') or '')

        if not self._is_become_enabled():
            return MULTIPATH_COMMAND

        normalized_become_method = ' '.join(become_method.split())
        if normalized_become_method in ('su', 'su -'):
            become_script = "current_user=$(whoami); echo {marker}${{current_user}}; exec {command}".format(
                marker=shlex.quote(BECOME_USER_MARKER),
                command=MULTIPATH_COMMAND,
            )
            return "bash -lc " + shlex.quote(
                "printf '%s\\n' {password} | su - {user} -c {command}".format(
                    password=shlex.quote(become_password),
                    user=shlex.quote(become_user),
                    command=shlex.quote("bash -lc " + shlex.quote(become_script)),
                )
            )

        raise ValueError(f'unsupported become_method: {become_method}')

    def _is_command_not_found(self, rc, out, err):
        if rc == 127:
            return True
        command_error = self._detect_command_error(out, err)
        return bool(command_error)

    def _parse_path_line(self, line):
        match = PATH_LINE_PATTERN.search(line.strip())
        if not match:
            return None

        trailing = match.group(3).strip()
        status_tokens = trailing.split()
        lowered_tokens = [token.lower() for token in status_tokens]
        return {
            'host_channel': match.group(1),
            'device_name': match.group(2),
            'status_tokens': lowered_tokens,
            'running': 'running' in lowered_tokens,
            'abnormal_markers': [
                marker
                for marker in ABNORMAL_MARKERS
                if marker in lowered_tokens
            ],
            'line': line.strip(),
        }

    def _parse_output(self, stdout):
        lines = [
            line.rstrip()
            for line in (stdout or '').splitlines()
            if line.strip()
        ]
        group_statuses = []
        path_entries = []
        abnormal_lines = []

        for line in lines:
            lowered = line.lower()
            for status in GROUP_STATUS_PATTERN.findall(line):
                group_statuses.append(status.lower())

            path_entry = self._parse_path_line(line)
            if path_entry:
                path_entries.append(path_entry)

            if any(re.search(r'\b' + re.escape(marker) + r'\b', lowered) for marker in ABNORMAL_MARKERS):
                abnormal_lines.append(line.strip())

        return {
            'lines': lines,
            'group_statuses': group_statuses,
            'path_entries': path_entries,
            'abnormal_lines': abnormal_lines,
        }

    def run(self):
        try:
            command = self._build_command()
        except ValueError as exc:
            return self.fail(
                '권한 상승 설정 오류',
                message=str(exc),
            )

        become_password = str(self.get_application_credential_value('become_password', default='') or '')
        rc, out, err = self._ssh(command)
        self._mask_command_history(become_password)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'SSH 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if self._is_command_not_found(rc, out, err):
            return self.not_applicable(
                'multipath 명령을 사용할 수 없거나 멀티패스 환경이 아니어서 Path 이중화 점검은 대상미해당입니다.',
                raw_output=((out or '').strip() or (err or '').strip()),
            )

        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='multipath -ll 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        lines = (out or '').splitlines()
        if not lines:
            return self.fail(
                'Multipath 정보 없음',
                message='multipath -ll 결과가 비어 있습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        actual_become_user = ''
        if self._is_become_enabled():
            become_user = str(self.get_application_credential_value('become_user', default='root') or 'root').strip() or 'root'
            become_marker_line = next((line.strip() for line in lines if line.strip().startswith(BECOME_USER_MARKER)), '')
            if not become_marker_line:
                return self.fail(
                    '권한 상승 사용자 확인 실패',
                    message='권한 상승 후 사용자 확인 결과를 찾지 못했습니다.',
                    stdout=(out or '').strip(),
                    stderr=(err or '').strip(),
                )

            actual_become_user = become_marker_line.split(BECOME_USER_MARKER, 1)[1].strip()
            if actual_become_user != become_user:
                return self.fail(
                    '권한 상승 사용자 불일치',
                    message=f'권한 상승 사용자가 기대값과 다릅니다: expected={become_user}, actual={actual_become_user}',
                    stdout=(out or '').strip(),
                    stderr=(err or '').strip(),
                )

            lines = [line for line in lines if not line.strip().startswith(BECOME_USER_MARKER)]

        parsed = self._parse_output('\n'.join(lines))
        metrics = {
            'become_user': actual_become_user,
            'multipath_device_detected': bool(parsed['group_statuses'] or parsed['path_entries']),
            'path_group_count': len(parsed['group_statuses']),
            'path_entry_count': len(parsed['path_entries']),
            'running_path_count': sum(1 for entry in parsed['path_entries'] if entry.get('running')),
            'abnormal_path_count': len(parsed['abnormal_lines']),
            'group_statuses': parsed['group_statuses'],
            'path_entries': parsed['path_entries'],
            'abnormal_lines': parsed['abnormal_lines'],
        }

        if not metrics['multipath_device_detected']:
            return self.warn(
                metrics=metrics,
                thresholds={},
                reasons='multipath -ll 결과에서 멀티패스 장치 또는 경로 상태를 확인하지 못했습니다.',
                message='Path 이중화 구성이 없거나 상태 확인이 충분하지 않습니다.',
            )

        if parsed['abnormal_lines']:
            result = self.fail(
                'Multipath 경로 상태 비정상',
                message='multipath 경로 상태에 failed/faulty/offline 항목이 확인되었습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )
            result['metrics'] = metrics
            result['thresholds'] = {}
            result['reasons'] = '비정상 경로 상태가 검출되었습니다: ' + '; '.join(parsed['abnormal_lines'])
            return result

        if not all(status in ('active', 'enabled') for status in parsed['group_statuses']) or not all(
            entry.get('running') for entry in parsed['path_entries']
        ):
            return self.warn(
                metrics=metrics,
                thresholds={},
                reasons='경로 그룹 또는 물리 경로 상태를 추가 확인해야 합니다.',
                message='Path 이중화 상태 추가 확인 필요',
            )

        return self.ok(
            metrics=metrics,
            thresholds={},
            reasons='모든 경로 그룹이 active/enabled 상태이고 물리 경로가 running 상태입니다.',
            message='Path 이중화 점검 정상',
        )


CHECK_CLASS = Check
