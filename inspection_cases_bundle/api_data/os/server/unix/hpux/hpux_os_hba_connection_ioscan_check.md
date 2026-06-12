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

HPUX-REPLAY-28

# is_required

권고

# inspection_name

HBA 연결상태 점검

# inspection_content

HBA 연결 정상 유무를 점검한다.

# inspection_command

```bash
ioscan -fnC fc
```

# inspection_output

```text
Class     I  H/W Path        Driver      S/W State   H/W Type     Description
===========================================================================
fc        0  0/2/1/0         fcd         CLAIMED     INTERFACE    HP Fibre Channel Mass Storage Adapter
fc        1  0/2/1/1         fcd         CLAIMED     INTERFACE    HP Fibre Channel Mass Storage Adapter
```

# description

- `ioscan -fnC fc` 명령으로 Fibre Channel HBA가 OS에서 정상 인식되는지 확인한다.
- HBA 상태가 `CLAIMED`이면 드라이버가 장치를 정상 제어하는 상태로 본다.
- `UNCLAIMED`, `NO_HW`, `ERROR` 상태는 HBA, 드라이버, 슬롯, 펌웨어 문제 가능성이 있다.
- 실제 SAN 연결 상태와 속도는 스토리지 관리 도구, 스위치 포트, HBA 상세 명령으로 추가 확인한다.

- **양호**: 운영 대상 HBA가 모두 `CLAIMED` 상태로 확인되는 경우
- **경고**: HBA 누락 또는 `UNCLAIMED`, `NO_HW`, `ERROR` 상태가 있는 경우
- **확인 필요**: HBA 미구성 서버이거나 기대 HBA 수 기준이 없는 경우

# thresholds

[
    {id: null, key: "expected_hba_count", value: "0", sortOrder: 0}
,
{id: null, key: "allowed_hba_states", value: "CLAIMED", sortOrder: 1}
]

# inspection_script

# -*- coding: utf-8 -*-

import re
import time

from .common._base import BaseCheck
CONFIG = {'mode': 'ioscan',
 'device_class': 'fc',
 'allowed_states_key': 'allowed_hba_states',
 'expected_count_key': 'expected_hba_count',
 'case_name': 'hpux_os_hba_connection_ioscan_check',
 'item_name': 'HBA 연결상태 점검',
 'commands': ['ioscan -fnC fc'],
 'thresholds': [{'name': 'expected_hba_count', 'default': 0, 'type': 'int'},
                {'name': 'allowed_hba_states', 'default': 'CLAIMED', 'type': 'str'}]}
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

    def _evaluate(self, outputs):
        thresholds = self._thresholds()
        text = outputs[0]['stdout']
        device_class = CONFIG.get('device_class')
        allowed_key = CONFIG.get('allowed_states_key', 'allowed_states')
        expected_key = CONFIG.get('expected_count_key', 'expected_count')
        allowed_states = {token.upper() for token in self._split_list(thresholds.get(allowed_key, 'CLAIMED'))}
        expected_count = self._parse_int(thresholds.get(expected_key, 0), 0)
        devices = []
        abnormal = []

        for line in text.splitlines():
            parts = line.split()
            if len(parts) < 6 or parts[0].lower() != device_class:
                continue
            state = parts[4].upper()
            item = {
                'class': parts[0],
                'instance': parts[1],
                'hw_path': parts[2],
                'driver': parts[3],
                'state': state,
                'hw_type': parts[5],
                'description': ' '.join(parts[6:]),
            }
            devices.append(item)
            if state not in allowed_states:
                abnormal.append(item)

        if not devices:
            return self.fail('장치 정보 없음', message=f'ioscan 결과에서 {device_class} 장치를 찾지 못했습니다.', stdout=text)
        if expected_count and len(devices) < expected_count:
            return self.fail('장치 수 부족', message=f'{device_class} 장치 수가 기대값보다 적습니다: current={len(devices)}, expected={expected_count}', stdout=text)
        if abnormal:
            return self.fail('장치 상태 비정상', message='비정상 ioscan 상태가 확인되었습니다: ' + ', '.join(f"{x['hw_path']}={x['state']}" for x in abnormal), stdout=text)

        return self.ok(
            metrics={'device_count': len(devices), 'devices': devices, 'abnormal_devices': abnormal},
            thresholds={expected_key: expected_count, allowed_key: '|'.join(sorted(allowed_states))},
            reasons=f'{device_class} 장치 {len(devices)}개가 정상 상태입니다.',
            message=f'ioscan 기준 {CONFIG.get("item_name")} 점검이 정상 수행되었습니다.',
        )


CHECK_CLASS = Check
