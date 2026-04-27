# -*- coding: utf-8 -*-

import re
import shlex

from .common._base import BaseCheck


SYSCTL_COMMAND = 'sysctl -a'
BECOME_USER_MARKER = '__BECOME_USER__:'
DEFAULT_SYSCTL_KEY = 'net.ipv4.ip_forward'
DEFAULT_SYSCTL_VALUE = '1'


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
            return SYSCTL_COMMAND

        normalized_become_method = ' '.join(become_method.split())
        if normalized_become_method in ('su', 'su -'):
            become_script = "current_user=$(whoami); echo {marker}${{current_user}}; {command}".format(
                marker=BECOME_USER_MARKER,
                command=SYSCTL_COMMAND,
            )
            return "bash -lc " + shlex.quote(
                "printf '%s\\n' {password} | su - {user} -c {command}".format(
                    password=shlex.quote(become_password),
                    user=shlex.quote(become_user),
                    command=shlex.quote("bash -lc " + shlex.quote(become_script)),
                )
            )

        raise ValueError(f'unsupported become_method: {become_method}')

    def _normalize_value(self, text):
        return re.sub(r'\s+', ' ', str(text or '').strip())

    def _parse_sysctl_output(self, text):
        parsed = {}
        skipped_lines = []

        for raw_line in (text or '').splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if ' = ' not in line:
                skipped_lines.append(raw_line)
                continue

            key, value = line.split(' = ', 1)
            normalized_key = key.strip()
            if not normalized_key:
                skipped_lines.append(raw_line)
                continue
            parsed[normalized_key] = self._normalize_value(value)

        return parsed, skipped_lines

    def _get_effective_threshold_map(self):
        threshold_map = self.get_threshold_list_map()
        if threshold_map:
            return dict(threshold_map), 'api'

        return {
            DEFAULT_SYSCTL_KEY: DEFAULT_SYSCTL_VALUE,
        }, 'default'

    def run(self):
        threshold_map, threshold_source = self._get_effective_threshold_map()

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

        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='sysctl -a 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        lines = (out or '').splitlines()
        actual_become_user = ''
        output_lines = lines

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

            output_lines = [line for line in lines if not line.strip().startswith(BECOME_USER_MARKER)]

        output = '\n'.join(output_lines).strip()
        if not output:
            return self.fail(
                'sysctl 정보 없음',
                message='sysctl -a 결과가 비어 있습니다.',
                stdout='',
                stderr=(err or '').strip(),
            )

        parsed_map, skipped_lines = self._parse_sysctl_output(output)
        if not parsed_map:
            return self.fail(
                'sysctl 정보 파싱 실패',
                message='sysctl -a 결과에서 key = value 형식의 항목을 찾지 못했습니다.',
                stdout=output,
                stderr=(err or '').strip(),
            )

        missing_keys = []
        mismatched_items = []
        matched_items = []

        for key, raw_expected in threshold_map.items():
            expected_value = self._normalize_value(raw_expected)
            actual_value = parsed_map.get(key)
            if actual_value is None:
                missing_keys.append(key)
                continue

            if actual_value != expected_value:
                mismatched_items.append({
                    'key': key,
                    'expected_value': expected_value,
                    'actual_value': actual_value,
                })
                continue

            matched_items.append({
                'key': key,
                'expected_value': expected_value,
                'actual_value': actual_value,
            })

        if missing_keys:
            return self.fail(
                'sysctl 키 누락',
                message='필수 sysctl 키를 찾지 못했습니다: ' + ', '.join(missing_keys),
                stdout=output,
                stderr=(err or '').strip(),
            )

        if mismatched_items:
            return self.fail(
                'sysctl 값 불일치',
                message='일부 sysctl 설정값이 기준값과 다릅니다: ' + ', '.join(
                    f"{item['key']}(expected={item['expected_value']}, actual={item['actual_value']})"
                    for item in mismatched_items
                ),
                stdout=output,
                stderr=(err or '').strip(),
            )

        matched_summary = ', '.join(
            f"{item['key']}={item['actual_value']}"
            for item in matched_items
        )

        return self.ok(
            metrics={
                'become_user': actual_become_user,
                'threshold_source': threshold_source,
                'checked_key_count': len(threshold_map),
                'matched_key_count': len(matched_items),
                'matched_items': matched_items,
                'skipped_lines': skipped_lines,
            },
            thresholds={
                key: self._normalize_value(value)
                for key, value in threshold_map.items()
            },
            reasons='threshold_list에 정의된 모든 sysctl 키가 존재하며 기준값과 일치합니다: ' + matched_summary,
            message='sysctl 커널 파라미터 점검이 정상 수행되었습니다. 일치 항목: ' + matched_summary,
        )


CHECK_CLASS = Check
