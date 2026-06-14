# type_name

일상점검

# area_name

server

# category_name

상태점검

# application_type

unix

# application

hpux

# inspection_code

HPUX-REPLAY-24

# is_required

권고

# inspection_name

메모리 사용률

# inspection_content

메모리 사용률 확인

# inspection_command

```bash
swapinfo -tam
```

# inspection_output

```text
TYPE      AVAIL    USED    FREE  PCT  START/   LIMIT RESERVE  PRI  NAME
dev        8192    1024    7168   12%       0       -       -    1  /dev/dsk/c0t0d0s2
reserve       -       -    2048
memory    16384    9200    7184   56%
total     24576   10224   14352   42%
```

# description

- `swapinfo -tam` 명령의 `memory` 행을 기준으로 물리 메모리 사용량과 여유량을 확인한다.
- 사용 가능한 물리 메모리 비율이 낮고 여유 메모리 용량도 부족하면 메모리 압박 상태로 본다.
- 메모리 부족이 확인되면 과다 사용 프로세스, 최근 배치 작업, WAS/DB 메모리 설정을 확인한다.
- free가 총 메모리의 권장 비율 이상이거나 절대 여유량 기준을 만족하면 여유로 판단한다.

- **양호**: free 비율이 `FREE_MIN_RATIO_PCT` 이상이거나 free 용량이 `FREE_MIN_GB` 이상인 경우
- **경고**: free 비율이 `FREE_MIN_RATIO_PCT` 미만이고 free 용량이 `FREE_MIN_GB` 미만인 경우
- **확인 필요**: `swapinfo` 결과 확인 또는 메모리 행 파싱이 불가능한 경우

# thresholds

[
    {id: null, key: "FREE_MIN_RATIO_PCT", value: "20", sortOrder: 0}
,
{id: null, key: "FREE_MIN_GB", value: "2", sortOrder: 1}
]

# inspection_script

# -*- coding: utf-8 -*-

import re
import time

from .common._base import BaseCheck
CONFIG = {'mode': 'swap_usage',
 'swap_target': 'total',
 'case_name': 'hpux_memory_swap_swapinfo_check',
 'item_name': 'Paging Space',
 'commands': ['swapinfo -tam'],
 'thresholds': [{'name': 'FREE_MIN_RATIO_PCT', 'default': 20, 'type': 'int'},
                {'name': 'USED_MAX_PCT', 'default': 80, 'type': 'int'}]}
PARAMIKO_COMMAND_TIMEOUT_SEC = 30
SU_FAILURE_MESSAGES = (
    'su: sorry',
    'authentication fail',
    'login incorrect',
    'incorrect password',
    'permission denied',
)


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'

    PARAMIKO_PROFILE = 'linux'
    PARAMIKO_AUTH_METHOD = 'password'
    PARAMIKO_ALLOW_AGENT = False
    PARAMIKO_LOOK_FOR_KEYS = False
    PARAMIKO_TIMEOUT_SEC = 60
    PARAMIKO_BANNER_TIMEOUT_SEC = 60
    PARAMIKO_AUTH_TIMEOUT_SEC = 60
    PARAMIKO_READ_TIMEOUT_SEC = 1.0

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

    def _normalize_become_method(self):
        become_method = str(self.get_application_credential_value('become_method', default='su -') or 'su -').strip().lower()
        normalized_become_method = ' '.join(become_method.split())
        if normalized_become_method not in ('su', 'su -'):
            raise ValueError(f'unsupported become_method: {become_method}')
        return normalized_become_method





    def _find_su_failure(self, text):
        lowered = (text or '').lower()
        for phrase in SU_FAILURE_MESSAGES:
            if phrase in lowered:
                return phrase
        return ''

    def _make_wrapped_command(self, command, index):
        token = f'{int(time.time() * 1000000)}_{index}'
        begin_marker = f'__FAP_OUTPUT_BEGIN__{token}__'
        rc_marker = f'__FAP_CMD_RC__{token}__:'
        wrapped_command = (
            f"printf '{begin_marker}\\n'; "
            f'{command}; '
            f"printf '\\n{rc_marker}%s\\n' $?"
        )
        return {
            'command': command,
            'wrapped_command': wrapped_command,
            'begin_marker': begin_marker,
            'rc_marker': rc_marker,
        }

    def _extract_command_result(self, buffer, begin_marker, rc_marker):
        text = str(buffer or '').replace('\r', '')
        begin_pattern = re.compile(
            r'(?:^|\r?\n)' + re.escape(begin_marker) + r'\r?\n'
        )
        rc_pattern = re.compile(
            r'(?:^|\r?\n)' + re.escape(rc_marker) + r'(?P<rc>-?\d+)\r?\n?'
        )

        begin_match = begin_pattern.search(text)
        if not begin_match:
            raise ValueError('명령 출력 시작 마커를 찾지 못했습니다.')

        rc_match = rc_pattern.search(text, begin_match.end())
        if not rc_match:
            raise ValueError('명령 종료 코드를 찾지 못했습니다.')

        output = text[begin_match.end():rc_match.start()]
        return int(rc_match.group('rc')), output.strip('\n')

    def _build_command_sequence(self, command_specs):
        sequence = []
        become_command_count = 0

        if self._is_become_enabled():
            become_user = str(
                self.get_application_credential_value('become_user', default='root') or 'root'
            ).strip() or 'root'
            become_password = str(
                self.get_application_credential_value('become_password', default='') or ''
            )
            become_method = self._normalize_become_method()
            su_command = f'su - {become_user}' if become_method == 'su -' else f'su {become_user}'

            sequence.extend([
                {
                    'command': su_command,
                    'timeout': 1,
                    'ignore_prompt': True,
                },
                {
                    'command': become_password,
                    'timeout': 5,
                    'hide_command': True,
                },
            ])
            become_command_count = 2

        for spec in command_specs:
            sequence.append({
                'command': spec['wrapped_command'],
                'timeout': PARAMIKO_COMMAND_TIMEOUT_SEC,
            })

        return sequence, become_command_count

    def _run_wrapped_commands(self, raw_commands, mode=None):
        if isinstance(raw_commands, str):
            commands = [raw_commands]
        else:
            commands = list(raw_commands or [])

        if self._is_become_enabled():
            try:
                self._normalize_become_method()
            except ValueError as exc:
                return None, self.fail('권한 상승 설정 오류', message=str(exc))

        command_specs = [
            self._make_wrapped_command(command, index)
            for index, command in enumerate(commands, 1)
        ]
        sequence, become_command_count = self._build_command_sequence(command_specs)

        history_start = len(self._command_history)
        results = self._run_paramiko_commands(
            sequence,
            profile=self.PARAMIKO_PROFILE,
            timeout_sec=PARAMIKO_COMMAND_TIMEOUT_SEC,
        )

        # _run_paramiko_commands는 wrapper 명령과 password 입력을 history에 남긴다.
        # 최종 raw_output은 실제 점검 명령 기준으로 보여주기 위해 공용 기록을 정리한다.
        del self._command_history[history_start:]

        if not results:
            return None, self.fail(
                '점검 명령 실행 실패',
                message='Paramiko 명령 실행 결과가 비어 있습니다.',
            )

        first = results[0]
        if self._is_connection_error(first.get('rc'), first.get('stderr')):
            return None, self.fail(
                '호스트 연결 실패',
                message=(first.get('stderr') or 'SSH 연결 확인에 실패했습니다.').strip(),
                stderr=(first.get('stderr') or '').strip(),
            )

        if self._is_become_enabled():
            become_text = '\n'.join(
                (item.get('stdout') or item.get('raw_output') or item.get('stderr') or '')
                for item in results[:become_command_count]
            )
            auth_failure = self._find_su_failure(become_text)
            if auth_failure:
                return None, self.fail(
                    '권한 상승 실패',
                    message=auth_failure,
                    stdout=become_text.strip(),
                    stderr=auth_failure,
                )

        command_results = results[become_command_count:]
        if len(command_results) < len(command_specs):
            last = results[-1]
            return None, self.fail(
                '점검 명령 실행 실패',
                message='일부 점검 명령 결과를 수신하지 못했습니다.',
                stdout=(last.get('stdout') or '').strip(),
                stderr=(last.get('stderr') or '').strip(),
            )

        outputs = []
        mode = CONFIG.get('mode') if mode is None and 'CONFIG' in globals() else mode
        for spec, result in zip(command_specs, command_results):
            command = spec['command']
            prompt_rc = int(result.get('rc') or 0)
            prompt_err = result.get('stderr') or ''

            if self._is_connection_error(prompt_rc, prompt_err):
                self._record_command(command, prompt_rc, '', prompt_err)
                return None, self.fail(
                    '호스트 연결 실패',
                    message=(prompt_err or 'SSH 연결 확인에 실패했습니다.').strip(),
                    stderr=prompt_err.strip(),
                )

            if prompt_rc not in [0, 124]:
                out = result.get('stdout') or result.get('raw_output') or ''
                self._record_command(command, prompt_rc, out, prompt_err)
                return None, self.fail(
                    '점검 명령 실행 실패',
                    message=f'{command} 명령 실행 중 프롬프트 수신에 실패했습니다.',
                    stdout=out.strip(),
                    stderr=prompt_err.strip(),
                )

            buffer = result.get('stdout') or result.get('raw_output') or ''
            try:
                rc, out = self._extract_command_result(
                    buffer,
                    spec['begin_marker'],
                    spec['rc_marker'],
                )
            except ValueError as exc:
                self._record_command(command, 1, buffer, str(exc))
                return None, self.fail(
                    '점검 명령 실행 실패',
                    message=str(exc),
                    stdout=buffer.strip(),
                    stderr=str(exc),
                )

            self._record_command(command, rc, out, '')

            log_no_match = mode == 'log' and rc == 1 and not (out or '').strip()
            if rc != 0 and not log_no_match:
                return None, self.fail(
                    '점검 명령 실행 실패',
                    message=f'{command} 명령 실행에 실패했습니다.',
                    stdout=(out or '').strip(),
                    stderr='',
                )

            command_error = self._detect_command_error(out, '')
            if command_error and not log_no_match:
                return None, self.fail(
                    '점검 명령 실행 실패',
                    message=f'{command} 명령 출력에서 실행 오류가 확인되었습니다: {command_error}',
                    stdout=(out or '').strip(),
                    stderr='',
                )

            outputs.append({
                'command': command,
                'rc': rc,
                'stdout': (out or '').strip(),
                'stderr': '',
                'become_user': str(
                    self.get_application_credential_value('become_user', default='root') or 'root'
                ).strip() if self._is_become_enabled() else '',
            })

        return outputs, None


    def _run_commands(self):
        return self._run_wrapped_commands(
            CONFIG.get('commands', []),
            mode=CONFIG.get('mode'),
        )

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
        target = CONFIG.get('swap_target', 'total')
        selected = [row for row in rows if row['type'].lower() == target]
        if not selected:
            return self.fail('swap 정보 없음', message=f'swapinfo 결과에서 {target} 행을 찾지 못했습니다.', stdout=text)
        max_used = self._parse_float(thresholds.get('USED_MAX_PCT', 80), 80.0)
        min_free = self._parse_float(thresholds.get('FREE_MIN_RATIO_PCT', 20), 20.0)
        bad = []
        for row in selected:
            row['free_percent'] = round(100.0 - row['used_percent'], 2)
            if row['used_percent'] > max_used or row['free_percent'] < min_free:
                bad.append(row)
        if bad:
            return self.fail('swap 사용률 임계치 초과', message='swap 사용률/여유율 기준 초과: ' + ', '.join(f"{x['type']} used={x['used_percent']}%, free={x['free_percent']}%" for x in bad), stdout=text)
        max_row = max(selected, key=lambda item: item['used_percent'])
        return self.ok(metrics={'target_type': target, 'rows': selected, 'max_used_percent': max_row['used_percent']}, thresholds={'USED_MAX_PCT': max_used, 'FREE_MIN_RATIO_PCT': min_free}, reasons='swap 사용률과 여유율이 기준 이내입니다.', message='swapinfo 기준 swap 사용률 점검이 정상 수행되었습니다.')


CHECK_CLASS = Check
