# -*- coding: utf-8 -*-

import re
import shlex

from .common._base import BaseCheck


CONFIG = {'mode': 'log',
 'bad_key': 'cluster_bad_log_keywords',
 'ignore_key': 'cluster_ignore_log_keywords',
 'bad_patterns_text': 'status\\s+change.*offline|status\\s+change.*unknown|cluster\\s+error|communication\\s+failure|\\berror\\b',
 'ignore_patterns_text': 'status\\s+change.*online',
 'fail_error': '클러스터 장애 로그 감지',
 'item_name': '클러스터 로그',
 'base_command': 'tail -n 2000 /var/adm/cmcluster/cmcld.log',
 'case_name': 'hpux_log_cluster_serviceguard_check',
 'thresholds': [{'name': 'cluster_bad_log_keywords',
                 'default': 'status\\s+change.*offline|status\\s+change.*unknown|cluster\\s+error|communication\\s+failure|\\berror\\b',
                 'type': 'str'},
                {'name': 'cluster_ignore_log_keywords', 'default': 'status\\s+change.*online', 'type': 'str'}]}
BECOME_USER_MARKER = '__BECOME_USER__:'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def _thresholds(self):
        values = {}
        for spec in CONFIG.get('thresholds', []):
            name = spec.get('name')
            if not name:
                continue
            values[name] = self.get_threshold_var(
                name,
                default=spec.get('default'),
                value_type=spec.get('type') or 'str',
            )
        return values

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

    def _build_become_command(self, command):
        if not self._is_become_enabled():
            return command

        become_method = str(self.get_application_credential_value('become_method', default='su -') or 'su -').strip().lower()
        become_user = str(self.get_application_credential_value('become_user', default='root') or 'root').strip() or 'root'
        become_password = str(self.get_application_credential_value('become_password', default='') or '')
        normalized_become_method = ' '.join(become_method.split())
        if normalized_become_method not in ('su', 'su -'):
            raise ValueError(f'unsupported become_method: {become_method}')

        become_script = 'current_user=$(whoami); echo {marker}${{current_user}}; {command}'.format(
            marker=BECOME_USER_MARKER,
            command=command,
        )
        return "printf '%s\\n' {password} | su - {user} -c {command}".format(
            password=shlex.quote(become_password),
            user=shlex.quote(become_user),
            command=shlex.quote(become_script),
        )

    def _strip_become_marker(self, output):
        if not self._is_become_enabled():
            return output or '', ''

        lines = (output or '').splitlines()
        marker_line = next((line.strip() for line in lines if line.strip().startswith(BECOME_USER_MARKER)), '')
        if not marker_line:
            raise ValueError('권한 상승 후 사용자 확인 결과를 찾지 못했습니다.')

        actual_user = marker_line.split(BECOME_USER_MARKER, 1)[1].strip()
        expected_user = str(self.get_application_credential_value('become_user', default='root') or 'root').strip() or 'root'
        if actual_user != expected_user:
            raise ValueError(f'권한 상승 사용자가 기대값과 다릅니다: expected={expected_user}, actual={actual_user}')

        cleaned_lines = [line for line in lines if not line.strip().startswith(BECOME_USER_MARKER)]
        return '\n'.join(cleaned_lines).strip(), actual_user

    def _split_list(self, value):
        return [token.strip() for token in re.split(r'[|,\n]+', str(value or '')) if token.strip()]

    def _egrep_expression(self, patterns):
        return '|'.join(pattern for pattern in patterns if pattern)

    def _base_command(self):
        return CONFIG.get('base_command', 'dmesg')

    def _build_command(self, bad_patterns):
        expression = self._egrep_expression(bad_patterns)
        if not expression:
            return self._base_command()
        return f"{self._base_command()} | egrep -i {shlex.quote(expression)}"

    def _regex_matches(self, line, patterns):
        matched = []
        for pattern in patterns:
            try:
                if re.search(pattern, line, re.IGNORECASE):
                    matched.append(pattern)
            except re.error:
                if pattern.lower() in line.lower():
                    matched.append(pattern)
        return matched

    def run(self):
        thresholds = self._thresholds()
        bad_key = CONFIG.get('bad_key', 'bad_log_keywords')
        ignore_key = CONFIG.get('ignore_key', 'ignore_log_keywords')
        bad_patterns = self._split_list(thresholds.get(bad_key, CONFIG.get('bad_patterns_text', '')))
        ignore_patterns = self._split_list(thresholds.get(ignore_key, CONFIG.get('ignore_patterns_text', '')))
        command = self._build_command(bad_patterns)

        try:
            actual_command = self._build_become_command(command)
        except ValueError as exc:
            return self.fail('권한 상승 설정 오류', message=str(exc))

        become_password = str(self.get_application_credential_value('become_password', default='') or '')
        rc, out, err = self._ssh(actual_command)
        self._mask_command_history(become_password)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'SSH 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        try:
            clean_out, actual_become_user = self._strip_become_marker(out)
        except ValueError as exc:
            return self.fail(
                '권한 상승 사용자 확인 실패',
                message=str(exc),
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        if rc not in (0, 1):
            return self.fail(
                '점검 명령 실행 실패',
                message=f'{command} 명령 실행에 실패했습니다.',
                stdout=(clean_out or '').strip(),
                stderr=(err or '').strip(),
            )

        command_error = self._detect_command_error(clean_out, err)
        if command_error:
            return self.fail(
                '점검 명령 실행 실패',
                message=f'{command} 명령 출력에서 실행 오류가 확인되었습니다: {command_error}',
                stdout=(clean_out or '').strip(),
                stderr=(err or '').strip(),
            )

        lines = [line.strip() for line in (clean_out or '').splitlines() if line.strip()]
        ignored_lines = []
        bad_matches = []
        for line in lines:
            ignore_matches = self._regex_matches(line, ignore_patterns)
            if ignore_matches:
                ignored_lines.append({'line': line, 'matched_patterns': ignore_matches})
                continue
            matched = self._regex_matches(line, bad_patterns)
            if matched:
                bad_matches.append({'line': line, 'matched_patterns': matched})

        metrics = {
            'command': command,
            'command_rc': rc,
            'become_user': actual_become_user,
            'log_line_count': len(lines),
            'ignored_line_count': len(ignored_lines),
            'bad_match_count': len(bad_matches),
            'bad_matches': bad_matches,
            'ignored_lines': ignored_lines,
        }
        threshold_data = {
            bad_key: '|'.join(bad_patterns),
            ignore_key: '|'.join(ignore_patterns),
        }

        if bad_matches:
            return self.fail(
                CONFIG.get('fail_error', '장애 로그 감지'),
                message=(
                    f'{CONFIG.get("item_name")}에서 장애 키워드가 확인되었습니다. '
                    f'검출 건수={len(bad_matches)}, ignore 제외={len(ignored_lines)}, 기준={threshold_data[bad_key]}.'
                ),
                stdout=(clean_out or '').strip(),
            )

        return self.ok(
            metrics=metrics,
            thresholds=threshold_data,
            reasons=f'{CONFIG.get("item_name")} 장애 키워드가 확인되지 않았습니다.',
            message=f'{CONFIG.get("item_name")} 점검이 정상 수행되었습니다.',
        )


CHECK_CLASS = Check
