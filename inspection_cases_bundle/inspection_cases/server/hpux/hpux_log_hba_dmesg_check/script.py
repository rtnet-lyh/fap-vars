# -*- coding: utf-8 -*-

import re
import shlex

from .common._base import BaseCheck


BASE_COMMAND = 'dmesg'
BAD_KEY = 'hba_bad_log_keywords'
IGNORE_KEY = 'hba_ignore_log_keywords'
FAIL_ERROR = 'HBA 장애 로그 감지'
LOG_LABEL = 'HBA 장애 로그'
ITEM_LABEL = 'HBA 로그'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def _split_patterns(self, value):
        return [
            token.strip()
            for token in re.split(r'[|,\n]+', str(value or ''))
            if token.strip()
        ]

    def _matches_any(self, line, patterns):
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
        bad_raw = self.get_threshold_var(BAD_KEY, default='', value_type='str')
        ignore_raw = self.get_threshold_var(IGNORE_KEY, default='', value_type='str')
        bad_patterns = self._split_patterns(bad_raw)
        ignore_patterns = self._split_patterns(ignore_raw)

        if not bad_patterns:
            return self.fail(
                '임계치 미정의',
                message=f'{BAD_KEY} 값이 비어 있어 egrep 패턴을 만들 수 없습니다.',
            )

        command = f'{BASE_COMMAND} | egrep -i {shlex.quote("|".join(bad_patterns))}'
        rc, out, err = self._ssh(command)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'SSH 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if rc not in (0, 1):
            return self.fail(
                '점검 명령 실행 실패',
                message=f'{command} 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        if 'REPLAY_MISS:' in (err or ''):
            return self.fail(
                'replay 명령 불일치',
                message=(err or '').strip(),
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        command_error = self._detect_command_error(out, err)
        if command_error:
            return self.fail(
                '점검 명령 실행 실패',
                message=f'{command} 명령 출력에서 실행 오류가 확인되었습니다: {command_error}',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        ignored_lines = []
        bad_matches = []
        for line in [line.strip() for line in (out or '').splitlines() if line.strip()]:
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
            'log_line_count': len(ignored_lines) + len(bad_matches),
            'ignored_line_count': len(ignored_lines),
            'bad_match_count': len(bad_matches),
            'ignored_lines': ignored_lines,
            'bad_matches': bad_matches,
        }
        thresholds = {
            BAD_KEY: '|'.join(bad_patterns),
            IGNORE_KEY: '|'.join(ignore_patterns),
        }

        if bad_matches:
            return self.fail(
                FAIL_ERROR,
                message=(
                    f'{LOG_LABEL} {len(bad_matches)}건이 확인되었습니다. '
                    f'ignore 제외={len(ignored_lines)}건, 기준={thresholds[BAD_KEY]}.'
                ),
                stdout=(out or '').strip(),
            )

        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons=f'{LOG_LABEL}가 확인되지 않았습니다.',
            message=f'{ITEM_LABEL} 점검이 정상 수행되었습니다.',
        )


CHECK_CLASS = Check
