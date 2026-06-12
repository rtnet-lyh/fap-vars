# type_name

일상점검

# area_name

상태점검

# category_name

server

# application_type

unix

# application

hpux

# inspection_code

HPUX-REPLAY-18

# is_required

필수

# inspection_name

MEMORY 로그

# inspection_content

메모리 오류 에러로그 점검(Singlebit/Multibit Errors, Uncorrectable ECC Errors)

# inspection_command

```bash
dmesg | egrep -i 'ecc error|single[- ]?bit|multi[- ]?bit|uncorrectable'
```

# inspection_output

```text
Multi-bit ECC error detected on memory bank 1
```

# description

- `dmesg` 로그에서 메모리 ECC, single-bit, multi-bit, uncorrectable 오류를 확인한다.
- single-bit 오류가 반복되거나 multi-bit/uncorrectable 오류가 있으면 메모리 모듈 장애 가능성이 높다.
- 오류 발생 위치가 표시되면 해당 메모리 뱅크 또는 DIMM 정보를 확인한다.
- 장애 로그가 반복되면 벤더 점검과 부품 교체를 검토한다.

- **양호**: 메모리 ECC 또는 uncorrectable 오류 로그가 없는 경우
- **경고**: ECC, single-bit, multi-bit, uncorrectable 관련 로그가 확인되는 경우
- **확인 필요**: 로그 확인이 불가능하거나 오류 위치를 식별할 수 없는 경우

# thresholds

[
    {id: null, key: "memory_bad_log_keywords", value: "ecc\\s+error|single[- ]?bit|multi[- ]?bit|uncorrectable", sortOrder: 0}
,
{id: null, key: "memory_ignore_log_keywords", value: "", sortOrder: 1}
]

# inspection_script

# -*- coding: utf-8 -*-

import re
import shlex

from .common._base import BaseCheck


BASE_COMMAND = 'dmesg'
BAD_KEY = 'memory_bad_log_keywords'
IGNORE_KEY = 'memory_ignore_log_keywords'
FAIL_ERROR = 'MEMORY 장애 로그 감지'
LOG_LABEL = 'MEMORY 장애 로그'
ITEM_LABEL = 'MEMORY 로그'


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
