# -*- coding: utf-8 -*-

import re
import shlex

from .common._base import BaseCheck


BASE_COMMAND = 'dmesg'
DEFAULT_BAD_LOG_KEYWORDS = r'ecc\s+error|single[- ]?bit|multi[- ]?bit|uncorrectable'
DEFAULT_IGNORE_LOG_KEYWORDS = r''
REGEX_FLAGS = re.IGNORECASE
FAIL_ERROR = 'MEMORY 장애 로그 감지'
LOG_LABEL = 'MEMORY 장애 로그'
ITEM_LABEL = 'MEMORY 로그'


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

    def _build_commands(self, command):
        if not self._is_become_enabled():
            return [command]
        return [
            {'command': self._build_become_command(), 'timeout': 1, 'ignore_prompt': True},
            {'command': str(self.get_connection_value('become_password', default='') or ''), 'hide_command': True},
            command,
        ]

    def _run_check_command(self, command):
        try:
            results = self._run_paramiko_commands(self._build_commands(command))
        except ValueError as exc:
            return 1, '', str(exc)

        if not results:
            return 1, '', 'paramiko command result not found'

        result = results[-1]
        return result.get('rc'), result.get('stdout', ''), result.get('stderr', '')

    def _split_patterns(self, value):
        return [
            token.strip()
            for token in re.split(r'[,\n]+', str(value or ''))
            if token.strip()
        ]

    def _matches_any(self, line, patterns):
        matched = []
        for pattern in patterns:
            try:
                if re.search(pattern, line, REGEX_FLAGS):
                    matched.append(pattern)
            except re.error:
                if pattern.lower() in line.lower():
                    matched.append(pattern)
        return matched

    def run(self):
        bad_raw = self.get_threshold_var(
            'bad_log_keywords',
            default=DEFAULT_BAD_LOG_KEYWORDS,
            value_type='raw',
        )
        ignore_raw = self.get_threshold_var(
            'ignore_log_keywords',
            default=DEFAULT_IGNORE_LOG_KEYWORDS,
            value_type='raw',
        )
        bad_patterns = self._split_patterns(bad_raw)
        ignore_patterns = self._split_patterns(ignore_raw)

        if not bad_patterns:
            return self.fail(
                '임계치 미정의',
                message='장애 로그 기준이 비어 있어 egrep 패턴을 만들 수 없습니다.',
            )

        command = f'{BASE_COMMAND} | egrep -i {shlex.quote("|".join(bad_patterns))}'
        rc, out, err = self._run_check_command(command)
        text = (out or '').strip()
        stderr_text = (err or '').strip()

        command_error = self._detect_command_error(
            text,
            stderr_text,
            extra_patterns=[
                'permission denied',
                'illegal option',
                'invalid option',
                'usage:',
            ],
        )
        if command_error:
            return self.fail(
                '점검 명령 실행 실패',
                message=f'{ITEM_LABEL} 점검 명령 출력에서 실행 오류가 확인되었습니다: {command_error}',
                stdout=text,
                stderr=stderr_text,
            )

        if rc not in (0, 1):
            return self.fail(
                '점검 명령 실행 실패',
                message=f'{ITEM_LABEL} 점검 명령 종료코드가 rc={rc}로 반환되었습니다.',
                stdout=text,
                stderr=stderr_text,
            )

        ignored_lines = []
        bad_matches = []
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for line in lines:
            ignore_matches = self._matches_any(line, ignore_patterns)
            if ignore_matches:
                ignored_lines.append({
                    'line': line,
                    'matched_patterns': ignore_matches,
                })
                continue

            matched = self._matches_any(line, bad_patterns)
            if matched:
                bad_matches.append({
                    'line': line,
                    'matched_patterns': matched,
                })

        metrics = {
            'command': command,
            'command_rc': rc,
            'log_line_count': len(lines),
            'ignored_line_count': len(ignored_lines),
            'bad_match_count': len(bad_matches),
            'ignored_lines': ignored_lines,
            'bad_matches': bad_matches,
        }
        thresholds = {
            'bad_log_keywords': '|'.join(bad_patterns),
            'ignore_log_keywords': '|'.join(ignore_patterns),
        }

        if bad_matches:
            return self.fail(
                FAIL_ERROR,
                message=(
                    f'{LOG_LABEL} {len(bad_matches)}건이 확인되었습니다. '
                    f'ignore 제외={len(ignored_lines)}건, 기준={thresholds["bad_log_keywords"]}.'
                ),
                stdout=text,
                stderr=stderr_text,
            )

        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons=f'{LOG_LABEL}가 확인되지 않았습니다.',
            message=f'{ITEM_LABEL} 점검이 정상 수행되었습니다.',
        )


CHECK_CLASS = Check
