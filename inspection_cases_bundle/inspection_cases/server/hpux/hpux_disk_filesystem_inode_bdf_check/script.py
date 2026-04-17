# -*- coding: utf-8 -*-

import re
import shlex

from .common._base import BaseCheck


CONFIG = {'mode': 'inode_usage',
 'case_name': 'hpux_disk_filesystem_inode_bdf_check',
 'item_name': 'I-Node 사용률',
 'commands': ['bdf -i'],
 'thresholds': [{'name': 'INODE_USED_MAX_PCT', 'default': 80, 'type': 'int'}]}
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

    def _parse_bdf_rows(self, text, inode=False):
        rows = []
        skipped = []
        for line in text.splitlines()[1:]:
            parts = line.split()
            if not parts:
                continue
            percent_indexes = [idx for idx, token in enumerate(parts) if token.endswith('%')]
            if inode:
                if len(percent_indexes) < 2:
                    skipped.append(line)
                    continue
                usage_idx = percent_indexes[-1]
            else:
                if not percent_indexes:
                    skipped.append(line)
                    continue
                usage_idx = percent_indexes[0]
            usage = self._parse_int(parts[usage_idx], None)
            if usage is None:
                skipped.append(line)
                continue
            rows.append({'filesystem': parts[0], 'usage_percent': usage, 'mount_point': parts[-1], 'raw_line': line})
        return rows, skipped

    def _evaluate(self, outputs):
        thresholds = self._thresholds()
        text = outputs[0]['stdout']
        max_inode = self._parse_float(thresholds.get('INODE_USED_MAX_PCT', 80), 80.0)
        rows, skipped = self._parse_bdf_rows(text, inode=True)
        if not rows:
            return self.fail('I-Node 사용률 정보 없음', message='bdf -i 결과에서 inode 사용률을 찾지 못했습니다.', stdout=text)
        over = [row for row in rows if row['usage_percent'] >= max_inode]
        if over:
            return self.fail('I-Node 사용률 임계치 초과', message='임계치 초과 파일시스템: ' + ', '.join(f"{x['mount_point']}={x['usage_percent']}%" for x in over), stdout=text)
        max_row = max(rows, key=lambda item: item['usage_percent'])
        return self.ok(metrics={'filesystem_count': len(rows), 'max_inode_usage_percent': max_row['usage_percent'], 'max_inode_usage_mount_point': max_row['mount_point'], 'checked_filesystems': rows, 'skipped_lines': skipped}, thresholds={'INODE_USED_MAX_PCT': max_inode}, reasons=f'최대 I-Node 사용률 {max_row["usage_percent"]}%가 기준 미만입니다.', message='bdf -i 기준 I-Node 사용률 점검이 정상 수행되었습니다.')


CHECK_CLASS = Check
