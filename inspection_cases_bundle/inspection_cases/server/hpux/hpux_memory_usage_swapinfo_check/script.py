# -*- coding: utf-8 -*-

import re
import shlex

from .common._base import BaseCheck


CONFIG = {'mode': 'memory_usage',
 'case_name': 'hpux_memory_usage_swapinfo_check',
 'item_name': '메모리 사용률',
 'commands': ['swapinfo -tam'],
 'thresholds': [{'name': 'FREE_MIN_RATIO_PCT', 'default': 20, 'type': 'int'},
                {'name': 'FREE_MIN_GB', 'default': 2, 'type': 'int'}]}
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

    def _build_command(self, command):
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

    def _run_commands(self):
        outputs = []
        mode = CONFIG.get('mode')

        for command in CONFIG.get('commands', []):
            try:
                actual_command = self._build_command(command)
            except ValueError as exc:
                return None, self.fail('권한 상승 설정 오류', message=str(exc))

            become_password = str(self.get_application_credential_value('become_password', default='') or '')
            rc, out, err = self._ssh(actual_command)
            self._mask_command_history(become_password)

            if self._is_connection_error(rc, err):
                return None, self.fail(
                    '호스트 연결 실패',
                    message=(err or 'SSH 연결 확인에 실패했습니다.').strip(),
                    stderr=(err or '').strip(),
                )

            try:
                clean_out, actual_become_user = self._strip_become_marker(out)
            except ValueError as exc:
                return None, self.fail(
                    '권한 상승 사용자 확인 실패',
                    message=str(exc),
                    stdout=(out or '').strip(),
                    stderr=(err or '').strip(),
                )

            log_no_match = mode == 'log' and rc == 1 and not (clean_out or '').strip()
            if rc != 0 and not log_no_match:
                return None, self.fail(
                    '점검 명령 실행 실패',
                    message=f'{command} 명령 실행에 실패했습니다.',
                    stdout=(clean_out or '').strip(),
                    stderr=(err or '').strip(),
                )

            command_error = self._detect_command_error(clean_out, err)
            if command_error and not log_no_match:
                return None, self.fail(
                    '점검 명령 실행 실패',
                    message=f'{command} 명령 출력에서 실행 오류가 확인되었습니다: {command_error}',
                    stdout=(clean_out or '').strip(),
                    stderr=(err or '').strip(),
                )

            outputs.append({
                'command': command,
                'rc': rc,
                'stdout': (clean_out or '').strip(),
                'stderr': (err or '').strip(),
                'become_user': actual_become_user,
            })

        return outputs, None

    def _split_list(self, value):
        return [token.strip() for token in re.split(r'[|,\n]+', str(value or '')) if token.strip()]

    def _parse_float(self, value, default=None):
        try:
            return float(str(value).strip().rstrip('%'))
        except (TypeError, ValueError):
            return default

    def _parse_int(self, value, default=None):
        parsed = self._parse_float(value, default=None)
        if parsed is None:
            return default
        return int(parsed)

    def _combined_stdout(self, outputs):
        return '\n'.join(item.get('stdout', '') for item in outputs if item.get('stdout', '')).strip()

    def run(self):
        outputs, error = self._run_commands()
        if error:
            return error
        return self._evaluate(outputs)

    def _parse_swapinfo_rows(self, text):
        rows = []
        for line in text.splitlines():
            parts = line.split()
            if len(parts) < 5 or parts[0].upper() == 'TYPE':
                continue
            if not parts[4].endswith('%'):
                continue
            rows.append({'type': parts[0], 'avail_mb': self._parse_float(parts[1], 0.0), 'used_mb': self._parse_float(parts[2], 0.0), 'free_mb': self._parse_float(parts[3], 0.0), 'used_percent': self._parse_float(parts[4], 0.0), 'raw_line': line})
        return rows

    def _evaluate(self, outputs):
        thresholds = self._thresholds()
        text = outputs[0]['stdout']
        rows = self._parse_swapinfo_rows(text)
        memory = next((row for row in rows if row['type'].lower() == 'memory'), None)
        if not memory:
            return self.fail('메모리 정보 없음', message='swapinfo 결과에서 memory 행을 찾지 못했습니다.', stdout=text)
        min_free_ratio = self._parse_float(thresholds.get('FREE_MIN_RATIO_PCT', 20), 20.0)
        min_free_gb = self._parse_float(thresholds.get('FREE_MIN_GB', 2), 2.0)
        free_ratio = round((memory['free_mb'] / memory['avail_mb']) * 100, 2) if memory['avail_mb'] else 0.0
        free_gb = round(memory['free_mb'] / 1024.0, 2)
        if free_ratio < min_free_ratio and free_gb < min_free_gb:
            return self.fail('사용 가능 메모리 부족', message=f'free_ratio={free_ratio}%, free_gb={free_gb}GB가 기준보다 낮습니다.', stdout=text)
        return self.ok(metrics={'memory_total_mb': memory['avail_mb'], 'memory_used_mb': memory['used_mb'], 'memory_free_mb': memory['free_mb'], 'memory_used_percent': memory['used_percent'], 'memory_free_percent': free_ratio, 'memory_free_gb': free_gb}, thresholds={'FREE_MIN_RATIO_PCT': min_free_ratio, 'FREE_MIN_GB': min_free_gb}, reasons='사용 가능 메모리가 기준 이상입니다.', message='swapinfo 기준 메모리 사용률 점검이 정상 수행되었습니다.')


CHECK_CLASS = Check
