# -*- coding: utf-8 -*-

import os
import re
import shlex
import time
# 2026-05-07 생성 [조정희]
# [FAP 변경] Paramiko 세션 재사용 기능에서 프로세스 종료 정리(atexit)를 사용하기 위해 추가했습니다.
import atexit

from .helpers import NetworkHelper, VMwareHelper, WebHelper
from . import base_wrappers as _base_wrappers
from .utils.encoding import ANSI_ESCAPE_RE, decode_bytes, normalize_terminal_text
from .utils.options import (
    append_unique_preserve_order,
    build_paramiko_options_from_object,
    normalize_csv_tuple,
    parse_bool_option,
    parse_bool_strict,
    threshold_list_to_map,
)
from .utils.credentials import (
    credential_or_empty,
    credential_context_data,
    credential_value,
    preferred_credential_value,
)
from .utils.thresholds import (
    cast_threshold_value,
    get_threshold_value,
)
from .utils.command_result import (
    build_command_history_raw_output as _build_command_history_raw_output_value,
    build_paramiko_result as _build_paramiko_result_value,
    build_terminal_history_raw_output as _build_terminal_history_raw_output_value,
    build_virtual_raw_output as _build_virtual_raw_output_value,
    describe_rc as _describe_rc_value,
    detect_command_error as _detect_command_error_value,
    evaluate_policy_text as _evaluate_policy_text_value,
    extract_lines as _extract_lines_value,
    is_connection_error as _is_connection_error_value,
    is_not_applicable as _is_not_applicable_value,
    record_command as _record_command_value,
    record_terminal_event as _record_terminal_event_value,
    resolve_raw_output as _resolve_raw_output_value,
    strip_paramiko_command_output as _strip_paramiko_command_output_value,
)
from .utils.become import (
    normalize_become_method as _normalize_become_method_value,
    parse_unix_id_uid as _parse_unix_id_uid_value,
    validate_become_user as _validate_become_user_value,
)
from .utils.paramiko_config import (
    paramiko_auth_attempts as _paramiko_auth_attempts_value,
    load_paramiko_private_key as _load_paramiko_private_key_value,
)
from .utils.paramiko_session import (
    build_paramiko_become_key as _build_paramiko_become_key_value,
    build_paramiko_profile_key as _build_paramiko_profile_key_value,
    build_paramiko_session_key as _build_paramiko_session_key_value,
    close_paramiko_session as _close_paramiko_session_value,
    is_paramiko_session_alive as _is_paramiko_session_alive_value,
    paramiko_secret_hash as _paramiko_secret_hash_value,
)
from .utils.paramiko_commands import (
    compile_paramiko_patterns as _compile_paramiko_patterns_value,
    extract_paramiko_prompt as _extract_paramiko_prompt_value,
    normalize_paramiko_commands as _normalize_paramiko_commands_value,
    paramiko_buffer_endswith_prompt as _paramiko_buffer_endswith_prompt_value,
    paramiko_channel_closed as _paramiko_channel_closed_value,
    paramiko_command_matches_line as _paramiko_command_matches_line_value,
    paramiko_recv_ready as _paramiko_recv_ready_value,
    paramiko_sendline as _paramiko_sendline_value,
    redact_paramiko_command_text as _redact_paramiko_command_text_value,
)
from .utils.remote_execution import (
    build_solaris_become_commands as _build_solaris_become_commands_value,
    normalize_solaris_command_specs as _normalize_solaris_command_specs_value,
    verify_solaris_become_result as _verify_solaris_become_result_value,
)


DEFAULT_PASSWORD_PROMPT_PATTERNS = [r'(?:[Pp]assword|암호):\s*$']
SOLARIS_LEGACY_KEX_ALGORITHMS = (
    'diffie-hellman-group-exchange-sha1',
    'diffie-hellman-group14-sha1',
    'diffie-hellman-group1-sha1',
)
SOLARIS_LEGACY_HOST_KEY_ALGORITHMS = ('ssh-rsa',)
DIFFIE_HELLMAN_GROUP1_P = int(
    'FFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD129024E088A67CC74020BBEA63B139B22514A08798E3404DDEF9519B3'
    'CD3A431B302B0A6DF25F14374FE1356D6D51C245E485B576625E7EC6F44C42E9A63A3620FFFFFFFFFFFFFFFF',
    16,
)
PARAMIKO_PROFILES = {
    'generic_network': {
        'pager_patterns': [r'--More--', r'--- more ---', r'Press any key', r'More:\s*<space>'],
        'pager_response': ' ',
    },
    'linux': {
    
        'pager_patterns': [],
        'pager_response': ' ',
    },
    'solaris': {
        'pager_patterns': [],
        'pager_response': ' ',
        'extra_kex_algorithms': SOLARIS_LEGACY_KEX_ALGORITHMS,
        'extra_host_key_algorithms': SOLARIS_LEGACY_HOST_KEY_ALGORITHMS,
    },
    'cisco_ios': {
        'pager_patterns': [r'--More--', r'--More--\s*$', r'More:\s*<space>'],
        'pager_response': ' ',
    },
    'junos': {
        'pager_patterns': [r'---\(more[^\)]*\)---', r'--- more ---', r'--More--'],
        'pager_response': ' ',
    },
    'huawei_vrp': {
        'pager_patterns': [
            r'---- More ----',
            r'--- More ---',
            r'--More--',
            r'Press any key',
        ],
        'pager_response': ' ',
    },
}


# 2026-05-07 생성 [조정희]

# [FAP 변경 시작] 기존 _base.py에는 없던 Paramiko 세션 캐시/정리 유틸입니다.
# 세션 재사용 기능을 켰을 때만 이 캐시에 client/channel을 저장합니다.
# Runner 프로세스 안에서 Paramiko interactive shell을 재사용하기 위한 캐시.
# inspection_scan.py가 runner.py를 subprocess로 새로 실행하면 프로세스가 바뀌므로
# 이 캐시는 해당 runner 프로세스 안에서만 유지된다.
_PARAMIKO_SESSION_CACHE = {}


def _paramiko_secret_hash(value):
    return _paramiko_secret_hash_value(value)


def _close_cached_paramiko_session(session):
    return _close_paramiko_session_value(session)


def close_all_paramiko_sessions():
    for session in list(_PARAMIKO_SESSION_CACHE.values()):
        _close_cached_paramiko_session(session)
    _PARAMIKO_SESSION_CACHE.clear()


atexit.register(close_all_paramiko_sessions)
# [FAP 변경 끝] Paramiko 세션 캐시/정리 유틸 추가 구간입니다.


def decode_paramiko_bytes(value, preferred_encodings=None):
    return decode_bytes(value, preferred_encodings=preferred_encodings)


def normalize_paramiko_text(text):
    return normalize_terminal_text(text, ansi_escape_re=ANSI_ESCAPE_RE)


class BaseCheck:
    """점검 항목 공통 베이스 클래스.

    - 결과 포맷(`ok/warn/fail`)을 일관되게 생성한다.
    - 항목 코드/입력 payload 등 실행 컨텍스트는 `ctx`에서 참조한다.
    """

    ITEM_TYPE = 'python'
    # 기본은 호스트 접속 사용
    USE_HOST_CONNECTION = True
    # 기본 원격 연결 방식
    CONNECTION_METHOD = 'ssh'
    # SSH 명령 최대 대기 시간(초), None이면 runner 기본값 사용
    SSH_COMMAND_TIMEOUT_SEC = None
    # WinRM 사용 시 기본 쉘
    WINRM_SHELL = 'powershell'
    # Paramiko interactive shell defaults. Override in script.py when needed.
    PARAMIKO_PROFILE = 'generic_network'
    PARAMIKO_AUTH_METHOD = 'auto'
    PARAMIKO_KEY_FILENAME = '~/.ssh/id_rsa.pub'
    PARAMIKO_PRIVATE_KEY = None
    PARAMIKO_PRIVATE_KEY_PASSPHRASE = None
    PARAMIKO_ALLOW_AGENT = False
    PARAMIKO_LOOK_FOR_KEYS = False
    PARAMIKO_TIMEOUT_SEC = 5
    PARAMIKO_BANNER_TIMEOUT_SEC = 10
    PARAMIKO_AUTH_TIMEOUT_SEC = 10
    PARAMIKO_READ_TIMEOUT_SEC = 0.5
    PARAMIKO_ENABLE_MODE = False
    PARAMIKO_PROBE_PROMPT = True
    PARAMIKO_CONTINUE_ON_TIMEOUT = False
    PARAMIKO_BECOME = False
    PARAMIKO_BECOME_METHOD = ''
    PARAMIKO_BECOME_USER = ''
    PARAMIKO_BECOME_PASSWORD = None


    # 2026-05-07 생성 [조정희]
    # [FAP 변경 시작] 세션 재사용 on/off 스위치입니다.
    # 기본값 False: 원래 _base.py처럼 _run_paramiko_commands 호출마다 접속을 열고 닫는다.
    # True로 바꾸거나 FAP_PARAMIKO_REUSE_SESSION=1 환경변수를 주면 같은 runner 프로세스 안에서
    # host/port/user/profile 단위로 Paramiko shell 세션을 재사용한다.
    PARAMIKO_REUSE_SESSION = True
    # [FAP 변경 끝] 기본값이 False이므로 설정하지 않으면 기존 동작을 유지합니다.

    def __init__(self, ctx):
        # ctx에는 ssh 함수, 접속 정보, 임계치 등이 들어있다.
        self.ctx = ctx
        # raw_output 기본값 생성을 위해 명령 실행 이력을 누적한다.
        self._command_history = []
        self._terminal_history = []
        self._threshold_list_map_cache = None
        self.network_helper = NetworkHelper(self)
        self.vmware_helper = VMwareHelper(self)
        self.web_helper = WebHelper(self)

    def run(self):
        raise NotImplementedError

    def _ssh(self, cmd, become=False):
        """현재 항목의 host 컨텍스트로 명령을 1회 실행한다."""
        exec_cmd = cmd
        display_cmd = cmd
        if become:
            try:
                exec_cmd, display_cmd = self._build_ssh_become_command(cmd)
            except ValueError as exc:
                err = str(exc)
                self._record_command(str(cmd or ''), 1, '', err)
                return 1, '', err

        rc, out, err = self.ctx['ssh'](
            exec_cmd,
            self.ctx['host'],
            self.ctx['port'],
            self.ctx['user'],
            self.ctx['password'],
            self.ctx['ssh_options'],
        )
        self._record_command(display_cmd, rc, out, err)
        return rc, out, err

    def _build_ssh_become_config(self):
        raw_method = self._get_preferred_credential_value('become_method', 'su -')
        raw_user = self._get_preferred_credential_value('become_user', 'root')
        raw_password = self._get_preferred_credential_value('become_password', '')

        method = self._normalize_become_method(raw_method or 'su -')
        if method not in ('sudo', 'su', 'su -'):
            raise ValueError('unsupported ssh become_method: ' + str(raw_method))

        return {
            'method': method,
            'user': self._validate_become_user(raw_user),
            'password': '' if raw_password is None else str(raw_password),
        }

    def _build_ssh_become_command(self, cmd):
        config = self._build_ssh_become_config()
        method = config['method']
        user_arg = shlex.quote(config['user'])
        password_arg = shlex.quote(config['password'])
        display_password_arg = shlex.quote('*******')
        cmd_arg = shlex.quote(str(cmd or ''))

        prefix = "printf '%s\\n' {password} | ".format(password=password_arg)
        display_prefix = "printf '%s\\n' {password} | ".format(password=display_password_arg)

        if method == 'sudo':
            suffix = "sudo -S -p '' -u {user} -- sh -lc {cmd}".format(
                user=user_arg,
                cmd=cmd_arg,
            )
        elif method == 'su':
            suffix = "su {user} -c {cmd}".format(user=user_arg, cmd=cmd_arg)
        elif method == 'su -':
            suffix = "su - {user} -c {cmd}".format(user=user_arg, cmd=cmd_arg)
        else:
            raise ValueError('unsupported ssh become_method: ' + str(method))

        return prefix + suffix, display_prefix + suffix

    def _paramiko_options(self):
        return build_paramiko_options_from_object(self)

    def _resolve_paramiko_profile(self, profile=None):
        raw_profile = profile if profile is not None else getattr(self, 'PARAMIKO_PROFILE', 'generic_network')
        if isinstance(raw_profile, dict):
            resolved = dict(raw_profile)
        else:
            name = str(raw_profile or 'generic_network').strip().lower().replace('-', '_')
            if name not in PARAMIKO_PROFILES:
                raise ValueError(f'unknown paramiko profile: {raw_profile}')
            resolved = dict(PARAMIKO_PROFILES[name])

        resolved.setdefault('pager_patterns', [])
        resolved.setdefault('pager_response', ' ')
        return resolved

    def _normalize_paramiko_algorithm_list(self, values):
        return normalize_csv_tuple(values)

    def _append_paramiko_algorithms(self, base_values, extra_values):
        return append_unique_preserve_order(base_values, extra_values)

    def _configure_paramiko_legacy_kex_algorithms(self, transport, extra_kex_algorithms):
        if not extra_kex_algorithms:
            return

        kex_info = dict(getattr(transport, '_kex_info', {}))
        needs_sha1_kex = any(
            algorithm in extra_kex_algorithms
            for algorithm in SOLARIS_LEGACY_KEX_ALGORITHMS
        )
        if needs_sha1_kex:
            from hashlib import sha1
            from paramiko.kex_gex import KexGexSHA256
            from paramiko.kex_group14 import KexGroup14SHA256

            class KexGexSHA1(KexGexSHA256):
                name = 'diffie-hellman-group-exchange-sha1'
                hash_algo = sha1

            class KexGroup14SHA1(KexGroup14SHA256):
                name = 'diffie-hellman-group14-sha1'
                hash_algo = sha1

            class KexGroup1SHA1(KexGroup14SHA1):
                P = DIFFIE_HELLMAN_GROUP1_P
                name = 'diffie-hellman-group1-sha1'

            kex_info.update({
                'diffie-hellman-group-exchange-sha1': KexGexSHA1,
                'diffie-hellman-group14-sha1': KexGroup14SHA1,
                'diffie-hellman-group1-sha1': KexGroup1SHA1,
            })

        unknown_algorithms = [
            algorithm for algorithm in extra_kex_algorithms
            if algorithm not in kex_info
        ]
        if unknown_algorithms:
            raise ValueError('unknown paramiko kex algorithm: ' + ', '.join(unknown_algorithms))

        transport._kex_info = kex_info
        transport._preferred_kex = self._append_paramiko_algorithms(
            getattr(transport, '_preferred_kex', ()),
            extra_kex_algorithms,
        )

    def _configure_paramiko_legacy_host_key_algorithms(self, transport, extra_host_key_algorithms, paramiko_module):
        if not extra_host_key_algorithms:
            return

        key_info = dict(getattr(transport, '_key_info', {}))
        if 'ssh-rsa' in extra_host_key_algorithms:
            from cryptography.hazmat.primitives import hashes

            class LegacyRSAKey(paramiko_module.RSAKey):
                HASHES = dict(paramiko_module.RSAKey.HASHES)

            LegacyRSAKey.HASHES['ssh-rsa'] = hashes.SHA1
            LegacyRSAKey.HASHES['ssh-rsa-cert-v01@openssh.com'] = hashes.SHA1
            key_info['ssh-rsa'] = LegacyRSAKey

        unknown_algorithms = [
            algorithm for algorithm in extra_host_key_algorithms
            if algorithm not in key_info
        ]
        if unknown_algorithms:
            raise ValueError('unknown paramiko host key algorithm: ' + ', '.join(unknown_algorithms))

        transport._key_info = key_info
        transport._preferred_keys = self._append_paramiko_algorithms(
            getattr(transport, '_preferred_keys', ()),
            extra_host_key_algorithms,
        )

    def _build_paramiko_transport_factory(self, resolved_profile, paramiko_module):
        extra_kex_algorithms = self._normalize_paramiko_algorithm_list(
            resolved_profile.get('extra_kex_algorithms')
        )
        extra_host_key_algorithms = self._normalize_paramiko_algorithm_list(
            resolved_profile.get('extra_host_key_algorithms')
        )
        if not extra_kex_algorithms and not extra_host_key_algorithms:
            return None

        def transport_factory(sock, disabled_algorithms=None):
            transport = paramiko_module.Transport(sock, disabled_algorithms=disabled_algorithms)
            self._configure_paramiko_legacy_kex_algorithms(transport, extra_kex_algorithms)
            self._configure_paramiko_legacy_host_key_algorithms(
                transport,
                extra_host_key_algorithms,
                paramiko_module,
            )
            return transport

        return transport_factory

    def _normalize_paramiko_commands(self, commands):
        return _normalize_paramiko_commands_value(
            commands,
            bool_option_parser=self._parse_paramiko_bool_option,
        )

    def _compile_paramiko_patterns(self, patterns):
        return _compile_paramiko_patterns_value(patterns)

    def _parse_paramiko_bool_option(self, raw_value, option_name, command_index):
        try:
            return parse_bool_strict(raw_value)
        except ValueError as exc:
            raise ValueError(f'invalid paramiko {option_name} in command #{command_index}: {raw_value}') from exc

    def _paramiko_command_matches_line(self, command, line):
        return _paramiko_command_matches_line_value(command, line)

    def _redact_paramiko_command_text(self, text, command, display_command):
        return _redact_paramiko_command_text_value(text, command, display_command)

    def _extract_paramiko_prompt(self, text, command=None):
        return _extract_paramiko_prompt_value(
            text,
            command=command,
            command_matches_line_func=self._paramiko_command_matches_line,
        )

    def _paramiko_buffer_endswith_prompt(self, text, prompt):
        return _paramiko_buffer_endswith_prompt_value(text, prompt)

    def _paramiko_auth_attempts(self, auth_method):
        return _paramiko_auth_attempts_value(auth_method)

    def _load_paramiko_private_key(self, private_key, passphrase, paramiko_module):
        return _load_paramiko_private_key_value(private_key, passphrase, paramiko_module)

    def _build_paramiko_connect_kwargs(self, options, auth_attempt, paramiko_module):
        resolved_profile = options.get('resolved_profile') or self._resolve_paramiko_profile(options.get('profile'))
        kwargs = {
            'hostname': self.ctx.get('host'),
            'port': int(self.ctx.get('port') or 22),
            'username': self.ctx.get('user') or None,
            'timeout': float(options.get('timeout_sec', 10)),
            'banner_timeout': float(options.get('banner_timeout_sec', 10)),
            'auth_timeout': float(options.get('auth_timeout_sec', 10)),
            'allow_agent': bool(options.get('allow_agent', False)),
            'look_for_keys': bool(options.get('look_for_keys', False)),
        }
        transport_factory = self._build_paramiko_transport_factory(resolved_profile, paramiko_module)
        if transport_factory is not None:
            kwargs['transport_factory'] = transport_factory
        if auth_attempt == 'password':
            kwargs['password'] = self.ctx.get('password') or None
            kwargs['allow_agent'] = False
            kwargs['look_for_keys'] = False
            return kwargs

        passphrase = options.get('private_key_passphrase')
        private_key = options.get('private_key')
        if private_key:
            kwargs['pkey'] = self._load_paramiko_private_key(private_key, passphrase, paramiko_module)
        else:
            kwargs['key_filename'] = os.path.expanduser(str(options.get('key_filename') or '~/.ssh/id_rsa.pub'))
        if passphrase:
            kwargs['passphrase'] = passphrase
        return kwargs

    def _open_paramiko_client(self, options):
        import paramiko

        client_factory = self.ctx.get('paramiko_client_factory')
        last_error = None
        for auth_attempt in self._paramiko_auth_attempts(options.get('auth_method')):
            client = client_factory() if callable(client_factory) else paramiko.SSHClient()
            try:
                if hasattr(client, 'set_missing_host_key_policy'):
                    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                client.connect(**self._build_paramiko_connect_kwargs(options, auth_attempt, paramiko))
                return client
            except Exception as exc:
                last_error = exc
                try:
                    client.close()
                except Exception:
                    pass
                if str(options.get('auth_method') or 'auto').strip().lower() != 'auto':
                    break
        if last_error:
            raise last_error
        raise RuntimeError('paramiko authentication attempt was not configured')

    def _paramiko_recv_ready(self, channel):
        return _paramiko_recv_ready_value(channel)

    def _paramiko_channel_closed(self, channel):
        return _paramiko_channel_closed_value(channel)

    def _paramiko_sendline(self, channel, text):
        return _paramiko_sendline_value(channel, text)

    def _paramiko_expect(
        self,
        channel,
        timeout_sec,
        profile,
        prompt=None,
        extra_patterns=None,
        settle_timeout_sec=None,
        command=None,
    ):
        compiled_patterns = self._compile_paramiko_patterns(extra_patterns)
        pager_patterns = self._compile_paramiko_patterns(profile.get('pager_patterns') or [])
        pager_response = str(profile.get('pager_response', ' '))
        buffer = ''
        deadline = None if timeout_sec is None else (time.monotonic() + float(timeout_sec))
        settle_timeout = 0.5 if settle_timeout_sec is None else max(float(settle_timeout_sec), 0.0)
        if timeout_sec is not None:
            settle_timeout = min(settle_timeout, max(float(timeout_sec), 0.0))
        if settle_timeout <= 0:
            settle_timeout = 0.02
        idle_deadline = None

        while True:
            for pager_pattern in pager_patterns:
                pager_match = pager_pattern.search(buffer)
                if not pager_match:
                    continue
                buffer = buffer[:pager_match.start()] + buffer[pager_match.end():]
                if pager_response:
                    channel.send(pager_response)
                break

            learned_prompt = self._extract_paramiko_prompt(buffer, command=command)
            for idx, pattern in enumerate(compiled_patterns):
                match = pattern.search(buffer)
                if match:
                    consumed = buffer[:match.end()]
                    return {
                        'matched': True,
                        'timed_out': False,
                        'index': idx,
                        'text': consumed,
                        'match_text': match.group(0),
                        'pattern': pattern.pattern,
                        'match_kind': 'pattern',
                        'prompt': '',
                    }

            if prompt and self._paramiko_buffer_endswith_prompt(buffer, prompt):
                prompt_text = learned_prompt or str(prompt or '').rstrip()
                return {
                    'matched': True,
                    'timed_out': False,
                    'index': -1,
                    'text': buffer,
                    'match_text': prompt_text,
                    'pattern': '',
                    'match_kind': 'prompt',
                    'prompt': prompt_text,
                }

            if not prompt and idle_deadline is not None and time.monotonic() >= idle_deadline and learned_prompt:
                return {
                    'matched': True,
                    'timed_out': False,
                    'index': -1,
                    'text': buffer,
                    'match_text': learned_prompt,
                    'pattern': '',
                    'match_kind': 'prompt',
                    'prompt': learned_prompt,
                }

            if deadline is not None and time.monotonic() >= deadline:
                return {
                    'matched': False,
                    'timed_out': True,
                    'index': -1,
                    'text': buffer,
                    'match_text': '',
                    'pattern': '',
                    'match_kind': '',
                    'prompt': '',
                }

            if self._paramiko_channel_closed(channel):
                if not prompt and learned_prompt:
                    return {
                        'matched': True,
                        'timed_out': False,
                        'index': -1,
                        'text': buffer,
                        'match_text': learned_prompt,
                        'pattern': '',
                        'match_kind': 'prompt',
                        'prompt': learned_prompt,
                        'closed': True,
                    }
                return {
                    'matched': False,
                    'timed_out': False,
                    'index': -1,
                    'text': buffer,
                    'match_text': '',
                    'pattern': '',
                    'match_kind': '',
                    'prompt': '',
                    'closed': True,
                }

            if self._paramiko_recv_ready(channel):
                data = channel.recv(4096)
                if not data:
                    return {
                        'matched': False,
                        'timed_out': False,
                        'index': -1,
                        'text': buffer,
                        'match_text': '',
                        'pattern': '',
                        'match_kind': '',
                        'prompt': '',
                        'closed': True,
                    }
                buffer += normalize_paramiko_text(decode_paramiko_bytes(data))
                idle_deadline = time.monotonic() + settle_timeout
                continue

            time.sleep(0.02)

    def _strip_paramiko_command_output(self, command, text, prompt):
        return _strip_paramiko_command_output_value(
            command,
            text,
            prompt,
            command_matches_line_func=self._paramiko_command_matches_line,
        )

    def _build_paramiko_result(
        self,
        command,
        rc,
        stdout='',
        stderr='',
        raw_output='',
        timed_out=False,
        prompt='',
        display_command='',
        hide_command=False,
    ):
        return _build_paramiko_result_value(
            command,
            rc,
            stdout=stdout,
            stderr=stderr,
            raw_output=raw_output,
            timed_out=timed_out,
            prompt=prompt,
            display_command=display_command,
            hide_command=hide_command,
        )

    # 2026-05-07 생성 [조정희]
    # [FAP 변경 시작] 아래 helper들은 세션 재사용 여부 판정, 세션 키 생성, 캐시 조회/폐기를 위해 추가했습니다.
    def _paramiko_bool_option(self, value, default=False):
        return parse_bool_option(value, default)

    def _get_preferred_credential_value(self, key, default=None):
        return preferred_credential_value(
            self.get_application_credential_data(),
            self.get_connection_credential_data(),
            key,
            default,
        )

    def _normalize_become_method(self, value):
        return _normalize_become_method_value(value)

    def _validate_become_user(self, user):
        return _validate_become_user_value(user, error_prefix='invalid become_user')

    def _build_paramiko_become_config(self, become=None):
        if isinstance(become, dict):
            enabled = self._paramiko_bool_option(become.get('become', become.get('enabled', True)), True)
            method_default = self._get_preferred_credential_value(
                'become_method',
                getattr(self, 'PARAMIKO_BECOME_METHOD', '') or 'su -',
            )
            user_default = self._get_preferred_credential_value(
                'become_user',
                getattr(self, 'PARAMIKO_BECOME_USER', '') or 'root',
            )
            password_default = self._get_preferred_credential_value(
                'become_password',
                getattr(self, 'PARAMIKO_BECOME_PASSWORD', None),
            )
            raw_method = become.get('method', become.get('become_method', method_default))
            raw_user = become.get('user', become.get('become_user', user_default))
            raw_password = become.get('password', become.get('become_password', password_default))
        else:
            enabled = self._paramiko_bool_option(
                become if become is not None else getattr(self, 'PARAMIKO_BECOME', False),
                False,
            )
            raw_method = self._get_preferred_credential_value(
                'become_method',
                getattr(self, 'PARAMIKO_BECOME_METHOD', '') or 'su -',
            )
            raw_user = self._get_preferred_credential_value(
                'become_user',
                getattr(self, 'PARAMIKO_BECOME_USER', '') or 'root',
            )
            raw_password = self._get_preferred_credential_value(
                'become_password',
                getattr(self, 'PARAMIKO_BECOME_PASSWORD', None),
            )

        if not enabled:
            return None

        method = self._normalize_become_method(raw_method or 'su -')
        if method not in ('su', 'su -', 'sudo'):
            raise ValueError('unsupported paramiko become_method: ' + str(raw_method))

        return {
            'method': method,
            'user': self._validate_become_user(raw_user),
            'password': '' if raw_password is None else str(raw_password),
        }

    def _paramiko_become_key(self, become_config):
        return _build_paramiko_become_key_value(become_config)

    def _parse_unix_id_uid(self, output):
        return _parse_unix_id_uid_value(output, missing_uid='')

    def _paramiko_become_command(self, become_config):
        method = become_config.get('method')
        user = become_config.get('user') or 'root'
        if method == 'su':
            return 'su ' + user
        if method == 'su -':
            return 'su - ' + user
        if method == 'sudo':
            return "sudo -S -p 'FAP_SUDO_PASSWORD:' -iu " + shlex.quote(user)
        raise ValueError('unsupported paramiko become_method: ' + str(method))

    def _paramiko_verify_become(self, channel, current_prompt, command_timeout, read_timeout, resolved_profile, become_config):
        verify_command = 'id'
        self._paramiko_sendline(channel, verify_command)
        verify_result = self._paramiko_expect(
            channel,
            command_timeout,
            resolved_profile,
            prompt=(current_prompt or None),
            settle_timeout_sec=read_timeout,
            command=verify_command,
        )
        if not verify_result.get('matched'):
            raise RuntimeError('become verification prompt was not received')

        verify_prompt = str(verify_result.get('prompt') or current_prompt or '').rstrip()
        verify_output = self._strip_paramiko_command_output(
            verify_command,
            verify_result.get('text', ''),
            verify_prompt,
        )
        uid, user_name = self._parse_unix_id_uid(verify_output)
        expected_user = str(become_config.get('user') or 'root').strip() or 'root'
        if expected_user == 'root' and uid == '0':
            return verify_prompt
        if expected_user != 'root' and user_name == expected_user:
            return verify_prompt

        raise RuntimeError(
            '권한 상승 사용자 확인 실패: expected_user=%s, actual_user=%s, actual_uid=%s, output=%s'
            % (expected_user, user_name or '', uid or '', verify_output.strip())
        )

    def _paramiko_apply_become(self, channel, current_prompt, command_timeout, read_timeout, resolved_profile, become_config):
        if not become_config:
            return current_prompt

        command = self._paramiko_become_command(become_config)
        self._paramiko_sendline(channel, command)
        result = self._paramiko_expect(
            channel,
            command_timeout,
            resolved_profile,
            extra_patterns=DEFAULT_PASSWORD_PROMPT_PATTERNS + [r'FAP_SUDO_PASSWORD:\s*$'],
            settle_timeout_sec=read_timeout,
            command=command,
        )

        if result.get('matched') and result.get('match_kind') == 'pattern':
            password = become_config.get('password') or ''
            if password == '':
                raise ValueError('paramiko become_password is required for ' + str(become_config.get('method') or ''))
            self._paramiko_sendline(channel, password)
            result = self._paramiko_expect(
                channel,
                command_timeout,
                resolved_profile,
                settle_timeout_sec=read_timeout,
            )

        if not result.get('matched'):
            raise RuntimeError('become prompt was not received')

        become_prompt = str(result.get('prompt') or '').rstrip()
        if not become_prompt:
            raise RuntimeError('become prompt was not received')

        return self._paramiko_verify_become(
            channel,
            become_prompt,
            command_timeout,
            read_timeout,
            resolved_profile,
            become_config,
        )


    def _solaris_bool_option(self, value, default=False):
        """Solaris helper용 bool 파서.

        credential/API payload에서는 bool 값이 True/False뿐 아니라
        "true", "false", "1", "0" 같은 문자열로도 들어올 수 있으므로
        기존 Paramiko bool 파서와 동일한 기준으로 해석한다.
        """
        return self._paramiko_bool_option(value, default)

    def _get_solaris_become_config(self):
        """Solaris su 기반 권한상승 설정을 반환한다.

        우선순위는 application credential data -> connection credential data이다.
        기본 정책은 Solaris에서 sudo가 아니라 su/su - 를 사용하는 것이다.
        """
        connection_method = self.get_connection_value('become_method', 'su -')
        method = self.get_application_credential_value('become_method', connection_method)

        connection_user = self.get_connection_value('become_user', 'root')
        user = self.get_application_credential_value('become_user', connection_user)

        connection_password = self.get_connection_value('become_password', '')
        password = self.get_application_credential_value('become_password', connection_password)

        connection_become = self.get_connection_value('become', False)
        become = self.get_application_credential_value('become', connection_become)

        method = ' '.join(str(method or 'su -').strip().lower().split()) or 'su -'
        user = str(user or 'root').strip() or 'root'
        password = '' if password is None else str(password)

        return {
            'become': self._solaris_bool_option(become, False),
            'method': method,
            'user': user,
            'password': password,
        }

    def _solaris_become_enabled(self, become_required=False):
        """Solaris 명령 실행 시 su 기반 권한상승이 필요한지 판단한다."""
        if bool(become_required):
            return True
        return bool(self._get_solaris_become_config().get('become'))

    def _validate_solaris_become_user(self, user):
        """su 명령에 사용할 사용자명을 보수적으로 검증한다."""
        return _validate_become_user_value(user, error_prefix='invalid solaris become_user')

    def _normalize_solaris_command_specs(self, command_specs):
        """Solaris 점검 명령 spec을 검증하고 정규화한다.

        모든 실제 점검 명령은 {'command': '...', 'timeout': N} 형태여야 한다.
        timeout 누락을 허용하지 않아 항목별 대기 시간이 코드에 명확히 남도록 한다.
        """
        return _normalize_solaris_command_specs_value(command_specs)

    def _build_solaris_become_commands(self):
        """Solaris su/su - 기반 권한상승 command sequence를 만든다.

        SOLARIS_PATH를 export하거나 PATH를 강제로 확장하지 않는다.
        root 로그인 환경이 필요한 명령은 su - 를 통해 실행한다.
        """
        return _build_solaris_become_commands_value(
            self._get_solaris_become_config(),
            validate_user_func=self._validate_solaris_become_user,
        )

    def _verify_solaris_become_result(self, results):
        """su - 이후 /usr/bin/id 결과로 root 전환 성공 여부를 검증한다."""
        return _verify_solaris_become_result_value(results)

    def _run_solaris_commands(self, command_specs, become_required=False, timeout_sec=None, include_become_results=False):
        """Solaris 점검 명령을 Paramiko interactive shell로 실행한다.

        - 항목 스크립트는 이 helper를 통해 _run_paramiko_commands를 호출한다.
        - become_required=True 또는 credential become=true이면 su/su - 로 root 전환 후 실행한다.
        - SOLARIS_PATH 추가나 export PATH 방식은 사용하지 않는다.
        - 기본 반환값은 실제 점검 명령 결과만 반환한다.
          include_become_results=True이면 su/id 결과까지 포함한 전체 결과를 반환한다.
        """
        normalized_specs = self._normalize_solaris_command_specs(command_specs)
        profile = getattr(self, 'PARAMIKO_PROFILE', 'solaris') or 'solaris'

        if not self._solaris_become_enabled(become_required=become_required):
            return self._run_paramiko_commands(
                normalized_specs,
                profile=profile,
                timeout_sec=timeout_sec,
            )

        become_commands = self._build_solaris_become_commands()
        all_commands = become_commands + normalized_specs
        all_results = self._run_paramiko_commands(
            all_commands,
            profile=profile,
            timeout_sec=timeout_sec,
        )

        become_count = len(become_commands)
        become_results = all_results[:become_count]
        command_results = all_results[become_count:]
        verification = self._verify_solaris_become_result(become_results)
        self._solaris_last_become_results = become_results
        self._solaris_last_become_verification = verification

        if not verification.get('ok'):
            first_command = normalized_specs[0]
            failed_result = self._build_paramiko_result(
                first_command.get('command'),
                1,
                stdout=verification.get('stdout') or '',
                stderr=verification.get('message') or 'Solaris su 권한상승 실패',
                raw_output=verification.get('raw_output') or '',
                display_command=first_command.get('display_command') or first_command.get('command'),
                hide_command=bool(first_command.get('hide_command', False)),
            )
            self._record_command(
                failed_result.get('display_command') or failed_result.get('command'),
                failed_result.get('rc'),
                failed_result.get('stdout'),
                failed_result.get('stderr'),
            )
            if include_become_results:
                return become_results + [failed_result]
            return [failed_result]

        if include_become_results:
            return all_results
        return command_results

    def _paramiko_reuse_session_enabled(self):
        # 우선순위:
        # 1) runner ctx의 paramiko_reuse_session
        # 2) item_payload의 paramiko_reuse_session
        # 3) 환경변수 FAP_PARAMIKO_REUSE_SESSION
        # 4) 점검 클래스의 PARAMIKO_REUSE_SESSION
        # 기본값은 False라서 설정하지 않으면 기존 동작처럼 매번 close한다.
        ctx_value = self.ctx.get('paramiko_reuse_session')
        if ctx_value is not None:
            return self._paramiko_bool_option(ctx_value, False)

        payload = self.ctx.get('item_payload') or {}
        if isinstance(payload, dict) and payload.get('paramiko_reuse_session') is not None:
            return self._paramiko_bool_option(payload.get('paramiko_reuse_session'), False)

        env_value = os.environ.get('FAP_PARAMIKO_REUSE_SESSION')
        if env_value is not None:
            return self._paramiko_bool_option(env_value, False)

        return self._paramiko_bool_option(getattr(self, 'PARAMIKO_REUSE_SESSION', False), False)

    def _paramiko_profile_key(self, resolved_profile):
        return _build_paramiko_profile_key_value(
            resolved_profile,
            normalize_algorithm_list_func=self._normalize_paramiko_algorithm_list,
        )

    def _paramiko_session_key(self, options, resolved_profile, enable_required, become_config=None):
        return _build_paramiko_session_key_value(
            self.ctx,
            options,
            resolved_profile,
            enable_required,
            profile_key_func=self._paramiko_profile_key,
            become_key_func=self._paramiko_become_key,
            become_config=become_config,
        )

    def _paramiko_session_alive(self, session):
        return _is_paramiko_session_alive_value(session)

    def _discard_paramiko_session(self, key):
        if key is None:
            return
        session = _PARAMIKO_SESSION_CACHE.pop(key, None)
        _close_cached_paramiko_session(session)

    def _create_paramiko_session(
        self,
        options,
        resolved_profile,
        command_timeout,
        read_timeout,
        enable_required,
        become_config=None,
    ):
        client = self._open_paramiko_client(options)
        channel = client.invoke_shell(term='vt100', width=200, height=1000)

        try:
            if options.get('probe_prompt', True):
                channel.send('\n')

            initial = self._paramiko_expect(
                channel,
                command_timeout,
                resolved_profile,
                settle_timeout_sec=read_timeout,
            )

            current_prompt = str(initial.get('prompt') or '').rstrip()
            if not initial.get('matched') or not current_prompt:
                raise RuntimeError('prompt was not received after login')

            if enable_required and not current_prompt.endswith('#'):
                privilege_command = 'enable'
                self._paramiko_sendline(channel, privilege_command)

                enable_result = self._paramiko_expect(
                    channel,
                    command_timeout,
                    resolved_profile,
                    extra_patterns=DEFAULT_PASSWORD_PROMPT_PATTERNS,
                    settle_timeout_sec=read_timeout,
                    command=privilege_command,
                )

                if enable_result.get('matched') and enable_result.get('match_kind') == 'pattern':
                    password = self.get_connection_value('en_password', '')
                    if password in (None, ''):
                        raise ValueError('privilege password is required')

                    self._paramiko_sendline(channel, password)
                    enable_result = self._paramiko_expect(
                        channel,
                        command_timeout,
                        resolved_profile,
                        settle_timeout_sec=read_timeout,
                    )

                current_prompt = str(enable_result.get('prompt') or '').rstrip()
                if not enable_result.get('matched') or not current_prompt:
                    raise RuntimeError('enable prompt was not received')

            current_prompt = self._paramiko_apply_become(
                channel,
                current_prompt,
                command_timeout,
                read_timeout,
                resolved_profile,
                become_config,
            )

            return {
                'client': client,
                'channel': channel,
                'prompt': current_prompt,
                'profile': resolved_profile,
                'created_at': time.time(),
            }
        except Exception:
            try:
                channel.close()
            except Exception:
                pass
            try:
                client.close()
            except Exception:
                pass
            raise

    def _get_paramiko_session(
        self,
        options,
        resolved_profile,
        command_timeout,
        read_timeout,
        enable_required,
        become_config=None,
    ):
        reuse_enabled = self._paramiko_reuse_session_enabled()
        key = self._paramiko_session_key(options, resolved_profile, enable_required, become_config=become_config)

        if reuse_enabled:
            cached = _PARAMIKO_SESSION_CACHE.get(key)
            if self._paramiko_session_alive(cached):
                return key, cached, True
            self._discard_paramiko_session(key)

        session = self._create_paramiko_session(
            options,
            resolved_profile,
            command_timeout,
            read_timeout,
            enable_required,
            become_config=become_config,
        )

        if reuse_enabled:
            _PARAMIKO_SESSION_CACHE[key] = session

        return key, session, False
    # [FAP 변경 끝] Paramiko 세션 재사용 helper 추가 구간입니다.

    # 2026-05-07 생성 [조정희]
    # [FAP 변경 시작] 기존 _run_paramiko_commands를 세션 재사용 옵션을 지원하도록 수정했습니다.
    def _run_paramiko_commands(self, commands, profile=None, enable_mode=None, timeout_sec=None, become=None):
        """Paramiko interactive shell로 여러 CLI 명령을 한 세션에서 순차 실행한다.

        PARAMIKO_REUSE_SESSION=True이면 같은 runner 프로세스 안에서 동일한
        host/port/user/password/auth/profile/enable 조건의 shell 세션을 재사용한다.
        명령 timeout이나 예외로 prompt 상태가 불확실해지면 캐시된 세션을 폐기한다.
        become=True이면 credential 또는 class 속성의 become 설정으로 먼저 권한상승한 뒤
        같은 shell 세션에서 실제 명령만 실행한다. 기본값은 비활성이라 기존 호출 동작은 유지된다.
        """
        command_items = self._normalize_paramiko_commands(commands)
        if not command_items:
            return []

        first_command = command_items[0]['command']
        first_display_command = command_items[0].get('display_command', first_command)
        first_hide_command = bool(command_items[0].get('hide_command'))

        options = self._paramiko_options()
        resolved_profile = self._resolve_paramiko_profile(profile)
        options['resolved_profile'] = resolved_profile
        command_timeout = float(timeout_sec if timeout_sec is not None else options.get('timeout_sec', 10))
        read_timeout = float(options.get('read_timeout_sec', 0.5))
        continue_on_timeout = bool(options.get('continue_on_timeout', False))
        enable_required = (
            bool(getattr(self, 'PARAMIKO_ENABLE_MODE', False))
            if enable_mode is None
            else bool(enable_mode)
        )
        become_config = self._build_paramiko_become_config(become)

        session_key = None
        session = None
        channel = None
        current_prompt = ''
        should_discard_session = False
        results = []

        try:
            # 2026-05-07 생성 [조정희]
            # [FAP 변경] 기존에는 여기서 매번 _open_paramiko_client()/invoke_shell()을 직접 호출했습니다.
            # 이제는 설정값에 따라 캐시된 세션을 재사용하거나, 기존 방식처럼 새 세션을 생성합니다.
            session_key, session, reused = self._get_paramiko_session(
                options,
                resolved_profile,
                command_timeout,
                read_timeout,
                enable_required,
                become_config=become_config,
            )

            channel = session.get('channel')
            current_prompt = str(session.get('prompt') or '').rstrip()
            if channel is None or not current_prompt:
                raise RuntimeError('cached paramiko session is invalid')

            for command_item in command_items:
                command = command_item['command']
                display_command = command_item.get('display_command', command)
                hide_command = bool(command_item.get('hide_command'))
                item_timeout = command_item.get('timeout', command_timeout)
                ignore_prompt = command_item.get('ignore_prompt')
                if ignore_prompt is None:
                    ignore_prompt = continue_on_timeout

                self._paramiko_sendline(channel, command)
                received = self._paramiko_expect(
                    channel,
                    item_timeout,
                    resolved_profile,
                    prompt=(current_prompt or None),
                    settle_timeout_sec=read_timeout,
                    command=command,
                )

                timed_out = bool(received.get('timed_out', False))
                rc = 0 if received.get('matched') else 124
                stderr = ''
                if rc != 0:
                    stderr = 'PARAMIKO_COMMAND_TIMEOUT: prompt was not received'

                item_prompt = str(received.get('prompt') or '').rstrip()
                output = self._strip_paramiko_command_output(
                    command,
                    received.get('text', ''),
                    item_prompt,
                )

                raw_output = received.get('text', '')
                if hide_command:
                    raw_output = self._redact_paramiko_command_text(raw_output, command, display_command)

                item = self._build_paramiko_result(
                    command,
                    rc,
                    stdout=output,
                    stderr=stderr,
                    raw_output=raw_output,
                    timed_out=timed_out,
                    prompt=item_prompt,
                    display_command=display_command,
                    hide_command=hide_command,
                )
                results.append(item)
                self._record_command(display_command, item['rc'], item['stdout'], item['stderr'])

                if item['rc'] == 0 and item_prompt:
                    current_prompt = item_prompt
                    # 2026-05-07 생성 [조정희]
                    # [FAP 변경] 세션을 재사용할 수 있도록 마지막 정상 prompt를 캐시에 갱신합니다.
                    session['prompt'] = current_prompt
                elif timed_out and ignore_prompt:
                    # 호출자가 timeout 후 계속 진행하기를 원하면 세션은 남기되,
                    # 다음 expect가 prompt를 새로 학습할 수 있게 prompt를 비운다.
                    current_prompt = ''
                    session['prompt'] = ''
                elif item['rc'] != 0:
                    # prompt를 못 받은 세션은 이후 명령 출력과 섞일 수 있으므로 폐기한다.
                    should_discard_session = True

                if item['rc'] != 0 and not (ignore_prompt and timed_out):
                    break

        except Exception as exc:
            should_discard_session = True
            stderr = 'PARAMIKO_CONNECTION_ERROR: ' + str(exc)
            item = self._build_paramiko_result(
                first_command,
                255,
                stderr=stderr,
                display_command=first_display_command,
                hide_command=first_hide_command,
            )
            results.append(item)
            self._record_command(first_display_command, 255, '', stderr)
        finally:
            if should_discard_session:
                self._discard_paramiko_session(session_key)
            elif not self._paramiko_reuse_session_enabled():
                _close_cached_paramiko_session(session)

        return results
    # [FAP 변경 끝] _run_paramiko_commands 세션 재사용 지원 수정 구간입니다.

    def _run_paramiko(self, command, **kwargs):
        results = self._run_paramiko_commands([command], **kwargs)
        if not results:
            return 1, '', 'paramiko command is empty'
        result = results[0]
        return result['rc'], result['stdout'], result['stderr']

    def _open_terminal(
        self,
        pager_patterns=None,
        pager_response=' ',
        preferred_encodings=None,
        open_timeout_sec=None,
        default_timeout_sec=None,
    ):
        opener = self.ctx.get('open_terminal')
        if not callable(opener):
            raise RuntimeError('interactive terminal is not available for this item')

        return opener(
            history_callback=self._record_terminal_event,
            pager_patterns=pager_patterns,
            pager_response=pager_response,
            preferred_encodings=preferred_encodings,
            open_timeout_sec=open_timeout_sec,
            default_timeout_sec=default_timeout_sec,
        )

    # Network helper wrappers
    def _run_show(self, cmd):
        return self.network_helper.run_show(cmd)

    def _run_config(self, variant=None):
        return self.network_helper.run_config(variant=variant)

    def _section_vty(self, variant=None):
        return self.network_helper.section_vty(variant=variant)

    def _grep_lines(self, text, pattern):
        return self.network_helper.grep_lines(text, pattern)

    def _has(self, text, pattern):
        return self.network_helper.has(text, pattern)

    # Web helper wrappers
    ## UNUSED_IN_CURRENT_CASES:
    ## inspection_cases.zip 기준 직접 호출 없음.
    ## 운영 DB inline script 호환성을 위해 유지.
    def _source_dicts(self):
        return self.web_helper.source_dicts()

    def _get_source_value(self, *keys, **kwargs):
        return self.web_helper.get_source_value(*keys, **kwargs)

    ## UNUSED_IN_CURRENT_CASES:
    ## inspection_cases.zip 기준 직접 호출 없음.
    ## 운영 DB inline script 호환성을 위해 유지.
    def _get_list_value(self, *keys, **kwargs):
        return self.web_helper.get_list_value(*keys, **kwargs)

    def _resolve_base_url(self):
        return self.web_helper.resolve_base_url()

    def _build_url(self, path_or_url=None):
        return self.web_helper.build_url(path_or_url=path_or_url)

    ## UNUSED_IN_CURRENT_CASES:
    ## inspection_cases.zip 기준 직접 호출 없음.
    ## 운영 DB inline script 호환성을 위해 유지.
    def _new_cookie_jar(self):
        return self.web_helper.new_cookie_jar()

    def _request(self, path_or_url=None, method='GET', params=None, data=None, headers=None, follow_redirects=True, cookie_jar=None, timeout=5):
        return self.web_helper.request(
            path_or_url=path_or_url,
            method=method,
            params=params,
            data=data,
            headers=headers,
            follow_redirects=follow_redirects,
            cookie_jar=cookie_jar,
            timeout=timeout,
        )

    ## UNUSED_IN_CURRENT_CASES:
    ## inspection_cases.zip 기준 직접 호출 없음.
    ## 운영 DB inline script 호환성을 위해 유지.
    def _find_markers(self, text, markers):
        return self.web_helper.find_markers(text, markers)

    ## UNUSED_IN_CURRENT_CASES:
    ## inspection_cases.zip 기준 직접 호출 없음.
    ## 운영 DB inline script 호환성을 위해 유지.
    def _get_session_cookie_values(self, response=None, cookie_jar=None):
        return self.web_helper.get_session_cookie_values(response=response, cookie_jar=cookie_jar)

    ## UNUSED_IN_CURRENT_CASES:
    ## inspection_cases.zip 기준 직접 호출 없음.
    ## 운영 DB inline script 호환성을 위해 유지.
    def _extract_cookie_tokens(self, response=None, cookie_jar=None):
        return self.web_helper.extract_cookie_tokens(response=response, cookie_jar=cookie_jar)

    def _login(self, cookie_jar=None):
        return self.web_helper.login(cookie_jar=cookie_jar)

    ## UNUSED_IN_CURRENT_CASES:
    ## inspection_cases.zip 기준 직접 호출 없음.
    ## 운영 DB inline script 호환성을 위해 유지.
    def _make_multipart(self, fields, file_field, filename, content, content_type='application/octet-stream'):
        return self.web_helper.make_multipart(
            fields=fields,
            file_field=file_field,
            filename=filename,
            content=content,
            content_type=content_type,
        )

    # Windows/WinRM helper wrappers
    def _run_ps(self, command):
        return self._ssh(command)

    # 텍스트 결과를 정책 mode 기준으로 공통 판정한다.
    def _evaluate_policy_text(self, mode, text, rule, rc=None):
        return _base_wrappers.evaluate_policy_text(mode, text, rule, rc=rc)

    def _extract_lines(self, text, pattern):
        return _base_wrappers.extract_lines(text, pattern)

    def _detect_command_error(self, *texts, extra_patterns=None):
        return _base_wrappers.detect_command_error(*texts, extra_patterns=extra_patterns)

    def _to_mb(self, value):
        return _base_wrappers.to_mb(value)

    def _parse_mpstat_field(self, text, field_name):
        return _base_wrappers.parse_mpstat_field(text, field_name)

    def _is_not_applicable(self, rc, err):
        return _is_not_applicable_value(rc, err)

    def _is_connection_error(self, rc, err):
        return _is_connection_error_value(rc, err)

    def _record_command(self, cmd, rc, out, err):
        return _base_wrappers.record_command(self._command_history, cmd, rc, out, err)

    def _record_terminal_event(self, event):
        return _base_wrappers.record_terminal_event(self._terminal_history, event)

    def get_threshold_list_map(self):
        """item_payload.threshold_list를 {name: value1} 딕셔너리로 변환한다."""
        if self._threshold_list_map_cache is not None:
            return self._threshold_list_map_cache

        payload = self.ctx.get('item_payload') or {}
        threshold_list = payload.get('threshold_list') or []
        self._threshold_list_map_cache = threshold_list_to_map(threshold_list)
        return self._threshold_list_map_cache

    # application 계정이 필요한 항목은 아래 헬퍼로 조회한다.
    # 예)
    #   app_cred = self.get_application_credential()
    #   app_user = self.get_application_credential_value('username')
    #   app_password = self.get_application_credential_value('password')
    #
    # 기본 접속 계정/장비 계정이 필요한 항목은 connection 헬퍼를 사용한다.
    # 예)
    #   conn_type = self.get_connection_credential().get('credential_type_name')
    #   conn_user = self.get_connection_value('username')
    #   enable_password = self.get_connection_value('en_password')
    def get_application_credential(self):
        """현재 항목에 매핑된 application credential 원본을 반환한다."""
        return credential_or_empty(self.ctx.get('application_credential'))

    def get_connection_credential(self):
        """현재 항목에 매핑된 connection credential 원본을 반환한다."""
        return credential_or_empty(self.ctx.get('connection_credential'))

    def get_connection_credential_data(self):
        """현재 항목에 매핑된 connection credential data를 반환한다."""
        return credential_context_data(
            self.ctx,
            'connection_credential_data',
            fallback_credential=self.get_connection_credential(),
        )

    def get_connection_value(self, key, default=None):
        """connection credential data에서 key 값을 조회한다."""
        return credential_value(self.get_connection_credential_data(), key, default)

    def get_application_credential_data(self):
        """현재 항목에 매핑된 application credential data를 반환한다."""
        return credential_context_data(
            self.ctx,
            'application_credential_data',
            fallback_credential=self.get_application_credential(),
        )

    def get_application_credential_value(self, key, default=None):
        """application credential data에서 key 값을 조회한다."""
        return credential_value(self.get_application_credential_data(), key, default)

    def _cast_threshold_var(self, raw_value, default, value_type=None):
        """원시 value1 값을 지정 타입으로 변환한다."""
        return _base_wrappers.cast_threshold_var(raw_value, default, value_type=value_type)

    def get_threshold_var(self, key, default=None, value_type=None, return_source=False):
        """threshold_list에서 key(name) 기준으로 값을 조회한다.

        - key가 없거나 변환 실패 시 default 반환
        - value_type 미지정 시 default 타입으로 자동 추론
        """
        return get_threshold_value(
            self.get_threshold_list_map(),
            key,
            default=default,
            value_type=value_type,
            return_source=return_source,
        )

    def get_host_vars(self):
        payload = self.ctx.get('item_payload') or {}
        host_vars = payload.get('host_vars') or {}
        return host_vars if isinstance(host_vars, dict) else {}

    def get_host_var(self, key, default=None):
        return self.get_host_vars().get(key, default)


    def _describe_rc(self, rc):
        return _describe_rc_value(rc)

    def _build_history_raw_output(self):
        return _base_wrappers.build_history_raw_output(self._command_history)

    def _build_virtual_raw_output(self, raw_output=None, stdout=None, stderr=None):
        return _base_wrappers.build_virtual_raw_output(raw_output=raw_output, stdout=stdout, stderr=stderr)

    def _build_terminal_history_raw_output(self):
        return _base_wrappers.build_terminal_history_raw_output(self._terminal_history)

    def _resolve_raw_output(self, raw_output=None, stdout=None, stderr=None):
        return _base_wrappers.resolve_raw_output(
            self._command_history,
            self._terminal_history,
            raw_output=raw_output,
            stdout=stdout,
            stderr=stderr,
        )

    def ok(self, metrics=None, thresholds=None, reasons=None, raw_output=None, message=None):
        # 정상 결과 포맷
        if isinstance(reasons, list):
            reasons = ", ".join(reasons)
        data = {
            'inspection_code': self.ctx.get('inspection_code'),
            'status': 'ok',
            'metrics': metrics or {},
            'thresholds': thresholds or {},
            'reasons': reasons or "",
            'raw_output': self._resolve_raw_output(raw_output=raw_output),
            'message': message or "",
        }
        if self.ctx.get('item_id') is not None:
            data['item_id'] = self.ctx.get('item_id')
        return data

    def warn(self, metrics=None, thresholds=None, reasons=None, raw_output=None, message=None):
        # 경고 결과 포맷
        if isinstance(reasons, list):
            reasons = ", ".join(reasons)
        if not message:
            message = reasons or ""
        data = {
            'inspection_code': self.ctx.get('inspection_code'),
            'status': 'warn',
            'metrics': metrics or {},
            'thresholds': thresholds or {},
            'reasons': reasons or "",
            'message': message,
            'raw_output': self._resolve_raw_output(raw_output=raw_output),
        }
        if self.ctx.get('item_id') is not None:
            data['item_id'] = self.ctx.get('item_id')
        return data

    def not_applicable(self, message='대상미해당', raw_output=None):
        """대상 제품/벤더/환경 미해당 시 표준 반환."""
        return self.warn(
            metrics={'applicable': False},
            reasons='대상미해당',
            message=message or '대상미해당',
            raw_output=raw_output,
        ) if not message else self.warn(
            metrics={'applicable': False},
            reasons=message,
            message=message,
            raw_output=raw_output,
        )

    def fail(self, error, message=None, stdout=None, stderr=None, raw_output=None, metrics=None, thresholds=None, reasons=None):
        # 실패 결과 포맷
        data = {
            'inspection_code': self.ctx.get('inspection_code'),
            'status': 'fail',
            'error': error,
        }
        if message is not None:
            data['message'] = message
        if stdout is not None:
            data['stdout'] = stdout
        if stderr is not None:
            data['stderr'] = stderr
        if metrics is not None:
            data['metrics'] = metrics        
        if thresholds is not None:
            data['thresholds'] = thresholds
        if reasons is not None:
            data['reasons'] = reasons
            
        data['raw_output'] = self._resolve_raw_output(raw_output=raw_output, stdout=stdout, stderr=stderr)
        if self.ctx.get('item_id') is not None:
            data['item_id'] = self.ctx.get('item_id')
        return data


class ShellCheck(BaseCheck):
    """Shell 기반 점검 항목 베이스 클래스."""

    ITEM_TYPE = 'shell'
    SCRIPT_PATH = None
    SCRIPT_INLINE = None

    def script_command(self):
        # 쉘 스크립트 실행 커맨드 구성
        if self.SCRIPT_PATH:
            return f"bash {self.SCRIPT_PATH}"
        if self.SCRIPT_INLINE:
            # inline script via bash -lc
            return "bash -lc " + __import__('json').dumps(self.SCRIPT_INLINE)
        return None
