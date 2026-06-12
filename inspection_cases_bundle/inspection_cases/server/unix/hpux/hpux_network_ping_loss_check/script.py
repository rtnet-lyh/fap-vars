# -*- coding: utf-8 -*-

import re
import time

from .common._base import BaseCheck
CONFIG = {'mode': 'ping',
 'case_name': 'hpux_network_ping_loss_check',
 'item_name': 'Ping Loss',
 'commands': ['ping 172.18.8.254 64 3'],
 'thresholds': [{'name': 'PING_LOSS_MAX_PCT', 'default': 0, 'type': 'int'},
                {'name': 'PING_LATENCY_MAX_MS', 'default': 100, 'type': 'int'},
                {'name': 'PING_TARGET', 'default': '172.18.8.254', 'type': 'str'}]}
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
        max_loss = self._parse_float(thresholds.get('PING_LOSS_MAX_PCT', 0), 0.0)
        max_latency = self._parse_float(thresholds.get('PING_LATENCY_MAX_MS', 100), 100.0)
        loss_match = re.search(r'(\d+)\s+packets\s+transmitted,\s+(\d+)\s+packets\s+received,\s+([0-9.]+)%\s+packet\s+loss', text, re.IGNORECASE)
        if not loss_match:
            return self.fail('Ping 결과 파싱 실패', message='packet loss 통계를 찾지 못했습니다.', stdout=text)
        transmitted = int(loss_match.group(1))
        received = int(loss_match.group(2))
        loss = float(loss_match.group(3))
        avg_match = re.search(r'min/avg/max\s*=\s*[0-9.]+/([0-9.]+)/[0-9.]+', text, re.IGNORECASE)
        avg_latency = float(avg_match.group(1)) if avg_match else 0.0
        if loss > max_loss or avg_latency > max_latency:
            return self.fail('Ping Loss 임계치 초과', message=f'loss={loss}%, avg_latency={avg_latency}ms가 기준을 초과했습니다.', stdout=text)
        return self.ok(metrics={'packets_transmitted': transmitted, 'packets_received': received, 'loss_percent': loss, 'avg_latency_ms': avg_latency}, thresholds={'PING_LOSS_MAX_PCT': max_loss, 'PING_LATENCY_MAX_MS': max_latency}, reasons='Ping 손실률과 지연 시간이 기준 이내입니다.', message='Ping Loss 점검이 정상 수행되었습니다.')


CHECK_CLASS = Check
