# -*- coding: utf-8 -*-

import codecs
import io
import os
import re
import shlex
import time
# 2026-05-07 생성 [조정희]
# [FAP 변경] Paramiko 세션 재사용 기능에서 프로세스 종료 정리(atexit)와 세션 키 해시(hashlib)를 사용하기 위해 추가했습니다.
import atexit
import hashlib

from .helpers import NetworkHelper, VMwareHelper, WebHelper


ANSI_ESCAPE_RE = re.compile(r'(?:\x1B\[[0-?]*[ -/]*[@-~]|\x1B\][^\x07]*(?:\x07|\x1B\\))')
DEFAULT_PASSWORD_PROMPT_PATTERNS = [r'(?:[Pp]assword|암호):\s*$']
PARAMIKO_PROFILES = {
    'generic_network': {
        'pager_patterns': [r'--More--', r'--- more ---', r'Press any key', r'More:\s*<space>', r'---\(more\s?\d{0,4}%?\)---'],
        'pager_response': ' ',
    },
    'linux': {
    
        'pager_patterns': [],
        'pager_response': ' ',
    },
    'solaris': {
        'pager_patterns': [],
        'pager_response': ' ',
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
    if value in (None, ''):
        return ''
    return hashlib.sha1(str(value).encode('utf-8')).hexdigest()


def _close_cached_paramiko_session(session):
    if not isinstance(session, dict):
        return

    channel = session.get('channel')
    client = session.get('client')

    if channel is not None:
        try:
            channel.close()
        except Exception:
            pass

    if client is not None:
        try:
            client.close()
        except Exception:
            pass


def close_all_paramiko_sessions():
    for session in list(_PARAMIKO_SESSION_CACHE.values()):
        _close_cached_paramiko_session(session)
    _PARAMIKO_SESSION_CACHE.clear()


atexit.register(close_all_paramiko_sessions)
# [FAP 변경 끝] Paramiko 세션 캐시/정리 유틸 추가 구간입니다.


def decode_paramiko_bytes(value, preferred_encodings=None):
    if value is None:
        return value
    if not isinstance(value, bytes):
        return str(value)
    if not value:
        return ''

    candidates = []
    if value.startswith(codecs.BOM_UTF8):
        candidates.append('utf-8-sig')
    candidates.append('utf-8')
    if value.startswith(codecs.BOM_UTF16_LE):
        candidates.append('utf-16-le')
    elif value.startswith(codecs.BOM_UTF16_BE):
        candidates.append('utf-16-be')
    elif b'\x00' in value:
        candidates.extend(['utf-16-le', 'utf-16-be'])
    for encoding in preferred_encodings or ():
        if encoding:
            candidates.append(str(encoding).strip())
    candidates.extend(['cp949', 'euc-kr', 'cp1252'])

    seen = set()
    for encoding in candidates:
        if not encoding or encoding in seen:
            continue
        seen.add(encoding)
        try:
            return value.decode(encoding)
        except (LookupError, UnicodeDecodeError):
            continue
    return value.decode('utf-8', 'replace')


def normalize_paramiko_text(text):
    normalized = str(text or '').replace('\x00', '').replace('\r\n', '\n').replace('\r', '\n')
    return ANSI_ESCAPE_RE.sub('', normalized)


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
    # False면 runner 기본 SSH multiplexing(ControlMaster) 옵션을 끈다.
    SSH_CONTROL_MASTER = None
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
    PARAMIKO_READ_TIMEOUT_SEC = 1.5
    PARAMIKO_ENABLE_MODE = False
    PARAMIKO_PROBE_PROMPT = True
    PARAMIKO_CONTINUE_ON_TIMEOUT = False
    PARAMIKO_BECOME = False
    PARAMIKO_BECOME_METHOD = ''
    PARAMIKO_BECOME_USER = ''
    PARAMIKO_BECOME_PASSWORD = None
    # AOS 용으로 추가
    PARAMIKO_IS_ELEVATED = False
    PARAMIKO_ELEVATE_FAILED = False

    # 2026-05-07 생성 [조정희]
    # [FAP 변경 시작] 세션 재사용 on/off 스위치입니다.
    # 기본값 False: 원래 _base.py처럼 _run_paramiko_commands 호출마다 접속을 열고 닫는다.
    # True로 바꾸거나 FAP_PARAMIKO_REUSE_SESSION=1 환경변수를 주면 같은 runner 프로세스 안에서
    # host/port/user/profile 단위로 Paramiko shell 세션을 재사용한다.
    PARAMIKO_REUSE_SESSION = False
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
        return {
            'profile': getattr(self, 'PARAMIKO_PROFILE', 'generic_network'),
            'auth_method': getattr(self, 'PARAMIKO_AUTH_METHOD', 'auto'),
            'key_filename': getattr(self, 'PARAMIKO_KEY_FILENAME', '~/.ssh/id_rsa.pub'),
            'private_key': getattr(self, 'PARAMIKO_PRIVATE_KEY', None),
            'private_key_passphrase': getattr(self, 'PARAMIKO_PRIVATE_KEY_PASSPHRASE', None),
            'allow_agent': getattr(self, 'PARAMIKO_ALLOW_AGENT', False),
            'look_for_keys': getattr(self, 'PARAMIKO_LOOK_FOR_KEYS', False),
            'timeout_sec': getattr(self, 'PARAMIKO_TIMEOUT_SEC', 10),
            'banner_timeout_sec': getattr(self, 'PARAMIKO_BANNER_TIMEOUT_SEC', 10),
            'auth_timeout_sec': getattr(self, 'PARAMIKO_AUTH_TIMEOUT_SEC', 10),
            'read_timeout_sec': getattr(self, 'PARAMIKO_READ_TIMEOUT_SEC', 0.5),
            'probe_prompt': getattr(self, 'PARAMIKO_PROBE_PROMPT', True),
            'continue_on_timeout': getattr(self, 'PARAMIKO_CONTINUE_ON_TIMEOUT', False),
        }

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

    def _normalize_paramiko_commands(self, commands):
        if isinstance(commands, str):
            raw_commands = commands.splitlines()
        elif isinstance(commands, (list, tuple)):
            raw_commands = commands
        else:
            raw_commands = [commands]

        normalized = []
        for idx, command in enumerate(raw_commands, 1):
            if isinstance(command, dict):
                text = str(command.get('command') or '').strip()
                if not text:
                    raise ValueError(f'paramiko command #{idx} requires non-empty command')

                item = {
                    'command': text,
                    'display_command': text,
                    'hide_command': False,
                    'delay': command.get('delay', 0)
                }
                if command.get('timeout') is not None:
                    try:
                        timeout = float(command.get('timeout'))
                    except Exception as exc:
                        raise ValueError(f'invalid paramiko timeout in command #{idx}: {command.get("timeout")}') from exc
                    if timeout < 0:
                        raise ValueError(f'invalid paramiko timeout in command #{idx}: {command.get("timeout")}')
                    item['timeout'] = timeout

                if 'ignore_prompt' in command:
                    item['ignore_prompt'] = self._parse_paramiko_bool_option(
                        command.get('ignore_prompt'),
                        option_name='ignore_prompt',
                        command_index=idx,
                    )

                raw_hide_command = command.get('hide_command')
                if raw_hide_command is not None:
                    item['hide_command'] = self._parse_paramiko_bool_option(
                        raw_hide_command,
                        option_name='hide_command',
                        command_index=idx,
                    )
                    if item['hide_command']:
                        item['display_command'] = '*******'

                normalized.append(item)
                continue

            text = str(command or '').strip()
            if text:
                normalized.append({
                    'command': text,
                    'display_command': text,
                    'hide_command': False,
                })
        return normalized

    def _compile_paramiko_patterns(self, patterns):
        return [re.compile(str(pattern), re.MULTILINE) for pattern in (patterns or [])]

    def _parse_paramiko_bool_option(self, raw_value, option_name, command_index):
        if isinstance(raw_value, bool):
            return raw_value

        text_value = str(raw_value or '').strip().lower()
        if text_value in ('1', 'true', 'yes', 'y', 'on'):
            return True
        if text_value in ('0', 'false', 'no', 'n', 'off'):
            return False
        raise ValueError(f'invalid paramiko {option_name} in command #{command_index}: {raw_value}')

    def _paramiko_command_matches_line(self, command, line):
        command_text = str(command or '').strip()
        line_text = str(line or '').strip()
        if not command_text or not line_text:
            return False
        return line_text == command_text or line_text.endswith(command_text)

    def _redact_paramiko_command_text(self, text, command, display_command):
        body = str(text or '')
        command_text = str(command or '')
        masked = str(display_command or command or '')
        if not body or not command_text or command_text == masked:
            return body
        return body.replace(command_text, masked)

    def _extract_paramiko_prompt(self, text, command=None):
        lines = str(text or '').splitlines()
        for line in reversed(lines):
            candidate = line.rstrip()
            if not candidate.strip():
                continue
            if self._paramiko_command_matches_line(command, candidate):
                continue
            return candidate
        return ''

    def _paramiko_buffer_endswith_prompt(self, text, prompt):
        prompt_text = str(prompt or '').rstrip()
        if not prompt_text:
            return False
        return str(text or '').rstrip().endswith(prompt_text)

    def _paramiko_auth_attempts(self, auth_method):
        method = str(auth_method or 'auto').strip().lower()
        if method == 'auto':
            return ['key', 'password']
        if method in ('key', 'password'):
            return [method]
        raise ValueError(f'unsupported paramiko auth_method: {auth_method}')

    def _load_paramiko_private_key(self, private_key, passphrase, paramiko_module):
        key_stream = io.StringIO(str(private_key))
        key_classes = [
            paramiko_module.RSAKey,
            paramiko_module.ECDSAKey,
            paramiko_module.Ed25519Key,
        ]
        dss_key = getattr(paramiko_module, 'DSSKey', None)
        if dss_key:
            key_classes.append(dss_key)

        last_error = None
        for key_cls in key_classes:
            key_stream.seek(0)
            try:
                return key_cls.from_private_key(key_stream, password=passphrase or None)
            except Exception as exc:
                last_error = exc
        if last_error:
            raise last_error
        raise ValueError('unsupported private key')

    def _build_paramiko_connect_kwargs(self, options, auth_attempt, paramiko_module):
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
        try:
            return bool(channel.recv_ready())
        except Exception:
            return False

    def _paramiko_channel_closed(self, channel):
        return bool(getattr(channel, 'closed', False))

    def _paramiko_sendline(self, channel, text, delay=0):        
        time.sleep(delay)
        channel.send(str(text or '') + '\n')

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
        body = str(text or '').rstrip()
        prompt_text = str(prompt or '').rstrip()
        if prompt_text and body.endswith(prompt_text):
            body = body[:-len(prompt_text)].rstrip()
        lines = body.splitlines()
        while lines and not lines[0].strip():
            lines = lines[1:]
        if lines and self._paramiko_command_matches_line(command, lines[0]):
            lines = lines[1:]
        return '\n'.join(lines).strip()

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
        return {
            'command': command,
            'display_command': display_command or command,
            'hide_command': bool(hide_command),
            'rc': rc,
            'stdout': stdout or '',
            'stderr': stderr or '',
            'raw_output': raw_output or '',
            'timed_out': bool(timed_out),
            'prompt': prompt or '',
        }

    # 2026-05-07 생성 [조정희]
    # [FAP 변경 시작] 아래 helper들은 세션 재사용 여부 판정, 세션 키 생성, 캐시 조회/폐기를 위해 추가했습니다.
    def _paramiko_bool_option(self, value, default=False):
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        text = str(value).strip().lower()
        if text in ('1', 'true', 'yes', 'y', 'on'):
            return True
        if text in ('0', 'false', 'no', 'n', 'off'):
            return False
        return default

    def _get_preferred_credential_value(self, key, default=None):
        for data in (
            self.get_application_credential_data(),
            self.get_connection_credential_data(),
        ):
            if not isinstance(data, dict) or key not in data:
                continue
            value = data.get(key)
            if value not in (None, ''):
                return value
        return default

    def _normalize_become_method(self, value):
        return ' '.join(str(value or '').strip().lower().split())

    def _validate_become_user(self, user):
        text = str(user or 'root').strip() or 'root'
        if not re.match(r'^[A-Za-z0-9_.-]+$', text):
            raise ValueError('invalid become_user: ' + text)
        return text

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
        if not become_config:
            return (False, '', '', '')
        return (
            True,
            str(become_config.get('method') or ''),
            str(become_config.get('user') or ''),
            _paramiko_secret_hash(become_config.get('password') or ''),
        )

    def _parse_unix_id_uid(self, output):
        match = re.search(r'(?:^|\s)uid=(\d+)(?:\(([^)]*)\))?', str(output or ''))
        if not match:
            return '', ''
        return match.group(1), match.group(2) or ''

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
        text = str(user or 'root').strip() or 'root'
        if not re.match(r'^[A-Za-z0-9_.-]+$', text):
            raise ValueError('invalid solaris become_user: ' + text)
        return text

    def _normalize_solaris_command_specs(self, command_specs):
        """Solaris 점검 명령 spec을 검증하고 정규화한다.

        모든 실제 점검 명령은 {'command': '...', 'timeout': N} 형태여야 한다.
        timeout 누락을 허용하지 않아 항목별 대기 시간이 코드에 명확히 남도록 한다.
        """
        if isinstance(command_specs, dict):
            raw_items = [command_specs]
        elif isinstance(command_specs, (list, tuple)):
            raw_items = list(command_specs)
        else:
            raise ValueError('solaris command_specs must be a list of command dictionaries')

        normalized = []
        for idx, item in enumerate(raw_items, 1):
            if not isinstance(item, dict):
                raise ValueError('solaris command #%s must be a command dictionary with timeout' % idx)

            command = str(item.get('command') or '').strip()
            if not command:
                raise ValueError('solaris command #%s requires non-empty command' % idx)
            if item.get('timeout') is None:
                raise ValueError('solaris command #%s requires timeout' % idx)

            try:
                timeout = float(item.get('timeout'))
            except Exception as exc:
                raise ValueError('invalid solaris timeout in command #%s: %s' % (idx, item.get('timeout'))) from exc
            if timeout < 0:
                raise ValueError('invalid solaris timeout in command #%s: %s' % (idx, item.get('timeout')))

            copied = dict(item)
            copied['command'] = command
            copied['timeout'] = timeout
            normalized.append(copied)

        return normalized

    def _build_solaris_become_commands(self):
        """Solaris su/su - 기반 권한상승 command sequence를 만든다.

        SOLARIS_PATH를 export하거나 PATH를 강제로 확장하지 않는다.
        root 로그인 환경이 필요한 명령은 su - 를 통해 실행한다.
        """
        config = self._get_solaris_become_config()
        method = config.get('method') or 'su -'
        if method not in ('su', 'su -'):
            raise ValueError('unsupported solaris become_method: ' + str(method))

        user = self._validate_solaris_become_user(config.get('user') or 'root')
        password = config.get('password') or ''
        if password == '':
            raise ValueError('solaris become_password is required for ' + method)

        su_command = 'su - ' + user if method == 'su -' else 'su - ' + user
        return [
            {
                'command': su_command,
                'timeout': 3,
                'ignore_prompt': True,
            },
            {
                'command': password,
                'display_command': '*******',
                'timeout': 5,
                'hide_command': True,
            },
            {
                'command': '/usr/bin/id',
                'display_command': 'id',
                'timeout': 5,
            },
        ]

    def _verify_solaris_become_result(self, results):
        """su - 이후 /usr/bin/id 결과로 root 전환 성공 여부를 검증한다."""
        copied_results = list(results or [])
        combined_stdout = '\n'.join(str(item.get('stdout') or '') for item in copied_results if isinstance(item, dict))
        combined_stderr = '\n'.join(str(item.get('stderr') or '') for item in copied_results if isinstance(item, dict))
        combined_raw = '\n'.join(str(item.get('raw_output') or '') for item in copied_results if isinstance(item, dict))
        combined_text = '\n'.join(part for part in (combined_stdout, combined_stderr, combined_raw) if part)
        combined_lower = combined_text.lower()

        auth_failure_markers = (
            'authentication failure',
            'sorry',
            'incorrect password',
            'permission denied',
            'su: failed',
            'su: incorrect',
            'su: authentication',
        )
        for marker in auth_failure_markers:
            if marker in combined_lower:
                return {
                    'ok': False,
                    'message': 'Solaris su 권한상승 실패: ' + marker,
                    'stdout': combined_stdout,
                    'stderr': combined_stderr,
                    'raw_output': combined_text,
                }

        id_result = None
        for item in copied_results:
            if not isinstance(item, dict):
                continue
            command = str(item.get('command') or '')
            display_command = str(item.get('display_command') or '')
            if command.endswith('/usr/bin/id') or display_command == 'id':
                id_result = item

        if id_result is None:
            return {
                'ok': False,
                'message': 'Solaris su 권한상승 검증 실패: id 결과가 없습니다.',
                'stdout': combined_stdout,
                'stderr': combined_stderr,
                'raw_output': combined_text,
            }

        id_text = '\n'.join(part for part in (
            str(id_result.get('stdout') or ''),
            str(id_result.get('raw_output') or ''),
            str(id_result.get('stderr') or ''),
        ) if part)
        if re.search(r'(?:^|\s)uid=0(?:\(|\s|$)', id_text):
            return {
                'ok': True,
                'message': 'Solaris su 권한상승 성공',
                'stdout': combined_stdout,
                'stderr': combined_stderr,
                'raw_output': combined_text,
            }

        return {
            'ok': False,
            'message': 'Solaris su 권한상승 검증 실패: uid=0(root)가 아닙니다.',
            'stdout': combined_stdout,
            'stderr': combined_stderr,
            'raw_output': combined_text,
        }

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

    def _verify_solaris_account_switch_result(self, expected_user, switch_result, whoami_result):
        """root 세션에서 su 전환 후 whoami 결과가 요청 계정인지 검증한다."""
        switched = switch_result if isinstance(switch_result, dict) else {}
        switch_rc = switched.get('rc', 1)
        switch_prompt_changed = switch_rc == 124 and switched.get('timed_out')
        if switch_rc != 0 and not switch_prompt_changed:
            return {
                'ok': False,
                'actual_user': '',
                'message': 'Solaris 계정 전환 실패: su 명령이 정상 종료되지 않았습니다.',
                'stdout': str(switched.get('stdout') or ''),
                'stderr': str(switched.get('stderr') or ''),
                'raw_output': str(switched.get('raw_output') or ''),
            }

        checked = whoami_result if isinstance(whoami_result, dict) else {}
        if checked.get('rc', 1) not in [0, 124]:
            return {
                'ok': False,
                'actual_user': '',
                'message': 'Solaris 계정 전환 검증 실패: whoami 명령이 정상 종료되지 않았습니다.',
                'stdout': str(checked.get('stdout') or ''),
                'stderr': str(checked.get('stderr') or ''),
                'raw_output': str(checked.get('raw_output') or ''),
            }

        stdout = str(checked.get('stdout') or '')
        is_actual_user = re.search(expected_user.lower(), stdout)
        output_lines = [line.strip() for line in stdout.splitlines() if line.strip()]
        actual_user = output_lines[-1] if output_lines else ''
        if is_actual_user: # actual_user == expected_user:
            return {
                'ok': True,
                'actual_user': actual_user,
                'message': 'Solaris 계정 전환 성공',
                'stdout': stdout,
                'stderr': str(checked.get('stderr') or ''),
                'raw_output': str(checked.get('raw_output') or ''),
            }

        return {
            'ok': False,
            'actual_user': actual_user,
            'message': (
                'Solaris 계정 전환 검증 실패: expected_user=%s, actual_user=%s'
                % (expected_user, actual_user or '')
            ),
            'stdout': stdout,
            'stderr': str(checked.get('stderr') or ''),
            'raw_output': str(checked.get('raw_output') or ''),
        }

    def _run_solaris_account_commands(
        self,
        user,
        command_specs,
        timeout_sec=None,
        include_switch_results=False,
    ):
        """Paramiko root become 후 Solaris 계정으로 su 전환해 점검 명령을 실행한다."""
        normalized_specs = self._normalize_solaris_command_specs(command_specs)
        expected_user = self._validate_solaris_become_user(user)
        switch_spec = {
            'command': 'su - ' + expected_user,
            'timeout': 2,
            'ignore_prompt': True,
        }
        whoami_spec = {
            'command': 'whoami',
            'timeout': 2,
            'ignore_prompt': True,
        }
        all_results = self._run_solaris_commands(
            [switch_spec, whoami_spec] + normalized_specs,
            timeout_sec=timeout_sec,
            become_required=True,
        )

        switch_result = all_results[0] if all_results else {}
        whoami_result = all_results[1] if len(all_results) > 1 else {}
        command_results = all_results[2:]
        verification = self._verify_solaris_account_switch_result(
            expected_user,
            switch_result,
            whoami_result,
        )
        self._solaris_last_account_switch_result = switch_result
        self._solaris_last_account_whoami_result = whoami_result
        self._solaris_last_account_switch_verification = verification

        if not verification.get('ok'):
            first_command = normalized_specs[0]
            failed_rc = switch_result.get('rc', 1) if isinstance(switch_result, dict) else 1
            if failed_rc == 0:
                failed_rc = whoami_result.get('rc', 1) if isinstance(whoami_result, dict) else 1
            if failed_rc == 0:
                failed_rc = 1
            failed_result = self._build_paramiko_result(
                first_command.get('command'),
                failed_rc,
                stdout=verification.get('stdout') or '',
                stderr=verification.get('stderr') or verification.get('message') or 'Solaris 계정 전환 실패',
                raw_output=verification.get('raw_output') or '',
                display_command=first_command.get('display_command') or first_command.get('command'),
                hide_command=bool(first_command.get('hide_command', False)),
            )
            if not failed_result.get('stderr'):
                failed_result['stderr'] = verification.get('message') or 'Solaris 계정 전환 실패'
            self._record_command(
                failed_result.get('display_command') or failed_result.get('command'),
                failed_result.get('rc'),
                failed_result.get('stdout'),
                failed_result.get('stderr'),
            )
            if include_switch_results:
                return [item for item in (switch_result, whoami_result, failed_result) if item]
            return [failed_result]

        if include_switch_results:
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
        if isinstance(resolved_profile, dict):
            pager_patterns = tuple(str(x) for x in (resolved_profile.get('pager_patterns') or []))
            pager_response = str(resolved_profile.get('pager_response', ' '))
            return (pager_patterns, pager_response)
        return str(resolved_profile or '')

    def _paramiko_session_key(self, options, resolved_profile, enable_required, become_config=None):
        return (
            self.ctx.get('host'),
            int(self.ctx.get('port') or 22),
            self.ctx.get('user') or '',
            _paramiko_secret_hash(self.ctx.get('password') or ''),
            str(options.get('auth_method') or 'auto'),
            str(options.get('key_filename') or ''),
            _paramiko_secret_hash(options.get('private_key') or ''),
            _paramiko_secret_hash(options.get('private_key_passphrase') or ''),
            bool(options.get('allow_agent', False)),
            bool(options.get('look_for_keys', False)),
            self._paramiko_profile_key(resolved_profile),
            bool(enable_required),
            self._paramiko_become_key(become_config),
        )

    def _paramiko_session_alive(self, session):
        if not isinstance(session, dict):
            return False

        client = session.get('client')
        channel = session.get('channel')
        if client is None or channel is None:
            return False

        try:
            if getattr(channel, 'closed', False):
                return False
        except Exception:
            return False

        try:
            transport = client.get_transport()
            if transport is None or not transport.is_active():
                return False
        except Exception:
            return False

        return True

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
        key = self._paramiko_session_key(options, resolved_profile, enable_required)

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
                delay = command_item.get('delay', 0)
                command = command_item['command']
                display_command = command_item.get('display_command', command)
                hide_command = bool(command_item.get('hide_command'))
                item_timeout = command_item.get('timeout', command_timeout)
                ignore_prompt = command_item.get('ignore_prompt')
                if ignore_prompt is None:
                    ignore_prompt = continue_on_timeout

                self._paramiko_sendline(channel, command, delay=delay)
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
    def _source_dicts(self):
        return self.web_helper.source_dicts()

    def _get_source_value(self, *keys, **kwargs):
        return self.web_helper.get_source_value(*keys, **kwargs)

    def _get_list_value(self, *keys, **kwargs):
        return self.web_helper.get_list_value(*keys, **kwargs)

    def _resolve_base_url(self):
        return self.web_helper.resolve_base_url()

    def _build_url(self, path_or_url=None):
        return self.web_helper.build_url(path_or_url=path_or_url)

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

    def _find_markers(self, text, markers):
        return self.web_helper.find_markers(text, markers)

    def _get_session_cookie_values(self, response=None, cookie_jar=None):
        return self.web_helper.get_session_cookie_values(response=response, cookie_jar=cookie_jar)

    def _extract_cookie_tokens(self, response=None, cookie_jar=None):
        return self.web_helper.extract_cookie_tokens(response=response, cookie_jar=cookie_jar)

    def _login(self, cookie_jar=None):
        return self.web_helper.login(cookie_jar=cookie_jar)

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
        if mode == 'pass_if_output':
            return bool(text)
        if mode == 'pass_if_no_output':
            return not bool(text)
        if mode == 'pass_if_regex':
            pattern = rule.get('pattern', '')
            return bool(re.search(pattern, text, re.IGNORECASE | re.MULTILINE))
        if mode == 'pass_if_not_regex':
            pattern = rule.get('pattern', '')
            return not bool(re.search(pattern, text, re.IGNORECASE | re.MULTILINE))
        if mode == 'pass_if_int_le':
            match = re.search(r'(-?\d+)', text)
            if not match:
                return False
            try:
                return int(match.group(1)) <= int(rule.get('threshold', 0))
            except Exception:
                return False
        if mode == 'pass_if_int_ge':
            match = re.search(r'(-?\d+)', text)
            if not match:
                return False
            try:
                return int(match.group(1)) >= int(rule.get('threshold', 0))
            except Exception:
                return False
        return rc == 0 if rc is not None else False

    def _extract_lines(self, text, pattern):
        return [ln.strip() for ln in (text or '').splitlines() if re.search(pattern, ln, re.IGNORECASE)]

    def _detect_command_error(self, *texts, extra_patterns=None):
        patterns = [
            'illegal option',
            'invalid option',
            'unknown option',
            'usage:',
            'command not found',
            'not found',
            'no such file',
            'cannot',
            '명령을 찾을 수 없습니다',
            '찾을 수 없습니다',
        ]
        if extra_patterns:
            patterns.extend([str(pattern).lower() for pattern in extra_patterns if pattern])

        for raw in texts:
            output = (raw or '').strip()
            if not output:
                continue
            output_lower = output.lower()
            for pattern in patterns:
                if pattern in output_lower:
                    return output.splitlines()[0].strip()
        return None

    def _to_mb(self, value):
        text = str(value or '').strip()
        if not text:
            return None
        match = re.match(r'^([0-9]+(?:\.[0-9]+)?)([kmgt]?i?b?|)$', text, re.IGNORECASE)
        if not match:
            return None

        number = float(match.group(1))
        unit = match.group(2).lower()
        if unit in ('', 'm', 'mb', 'mi', 'mib'):
            return number
        if unit in ('k', 'kb', 'ki', 'kib'):
            return number / 1024.0
        if unit in ('g', 'gb', 'gi', 'gib'):
            return number * 1024.0
        if unit in ('t', 'tb', 'ti', 'tib'):
            return number * 1024.0 * 1024.0
        if unit in ('b',):
            return number / (1024.0 * 1024.0)
        return None

    def _parse_mpstat_field(self, text, field_name):
        target = field_name.lower().lstrip('%')
        lines = [line.strip() for line in (text or '').splitlines() if line.strip()]
        header = None
        data = None

        for line in lines:
            lower = line.lower()
            if '%' + target in lower:
                header = re.split(r'\s+', line)
                continue
            if re.search(r'(^|\s)(average:)?\s*all(\s|$)', lower):
                data = re.split(r'\s+', line)

        if not header or not data:
            return None

        normalized = [token.lower() for token in header]
        column = '%' + target
        if column not in normalized:
            return None

        index = normalized.index(column)
        if index >= len(data):
            return None

        try:
            return round(float(data[index]), 2)
        except Exception:
            return None

    def _is_not_applicable(self, rc, err):
        text = (err or '').strip()
        if rc in (901, 902):
            return True
        if 'WINRM_UNAVAILABLE' in text or 'WINRM_EXEC_ERROR' in text:
            return True
        return False

    def _is_connection_error(self, rc, err):
        text = (err or '').strip().lower()
        if rc in (255, 901, 902):
            return True
        markers = (
            'no route to host',
            'network is unreachable',
            'connection refused',
            'connection timed out',
            'operation timed out',
            'could not resolve hostname',
            'host key verification failed',
            'permission denied',
            'connection reset by peer',
            'sshpass not installed',
            'winrm_unavailable',
            'winrm_exec_error',
            'paramiko_connection_error',
        )
        return any(marker in text for marker in markers)

    def _record_command(self, cmd, rc, out, err):
        self._command_history.append({
            'cmd': cmd,
            'rc': rc,
            'stdout': out if out is not None else '',
            'stderr': err if err is not None else '',
        })

    def _record_terminal_event(self, event):
        if not isinstance(event, dict):
            return
        copied = dict(event)
        copied['text'] = copied.get('text') if copied.get('text') is not None else ''
        self._terminal_history.append(copied)

    def get_threshold_list_map(self):
        """item_payload.threshold_list를 {name: value1} 딕셔너리로 변환한다."""
        if self._threshold_list_map_cache is not None:
            return self._threshold_list_map_cache

        payload = self.ctx.get('item_payload') or {}
        threshold_list = payload.get('threshold_list') or []
        mapped = {}

        if isinstance(threshold_list, list):
            for item in threshold_list:
                if not isinstance(item, dict):
                    continue
                name = str(item.get('name', '')).strip()
                if not name:
                    continue
                mapped[name] = item.get('value1')

        self._threshold_list_map_cache = mapped
        return mapped

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
        cred = self.ctx.get('application_credential') or {}
        if isinstance(cred, dict):
            return cred
        return {}

    def get_connection_credential(self):
        """현재 항목에 매핑된 connection credential 원본을 반환한다."""
        cred = self.ctx.get('connection_credential') or {}
        if isinstance(cred, dict):
            return cred
        return {}

    def get_connection_credential_data(self):
        """현재 항목에 매핑된 connection credential data를 반환한다."""
        data = self.ctx.get('connection_credential_data') or {}
        if isinstance(data, dict):
            return data
        cred = self.get_connection_credential()
        data = cred.get('data') or {}
        if isinstance(data, dict):
            return data
        return {}

    def get_connection_value(self, key, default=None):
        """connection credential data에서 key 값을 조회한다."""
        data = self.get_connection_credential_data()
        return data.get(key, default)

    def get_application_credential_data(self):
        """현재 항목에 매핑된 application credential data를 반환한다."""
        data = self.ctx.get('application_credential_data') or {}
        if isinstance(data, dict):
            return data
        cred = self.get_application_credential()
        data = cred.get('data') or {}
        if isinstance(data, dict):
            return data
        return {}

    def get_application_credential_value(self, key, default=None):
        """application credential data에서 key 값을 조회한다."""
        data = self.get_application_credential_data()
        return data.get(key, default)

    def _cast_threshold_var(self, raw_value, default, value_type=None):
        """원시 value1 값을 지정 타입으로 변환한다."""
        if value_type is None:
            if isinstance(default, bool):
                value_type = 'bool'
            elif isinstance(default, int):
                value_type = 'int'
            elif isinstance(default, float):
                value_type = 'float'
            else:
                value_type = 'str'

        if isinstance(value_type, type):
            if value_type is bool:
                value_type = 'bool'
            elif value_type is int:
                value_type = 'int'
            elif value_type is float:
                value_type = 'float'
            else:
                value_type = 'str'

        value_type = str(value_type).lower()

        if value_type == 'int':
            return int(str(raw_value).strip())
        if value_type == 'float':
            return float(str(raw_value).strip())
        if value_type == 'bool':
            text = str(raw_value).strip().lower()
            return text in ('1', 'true', 'y', 'yes', 'on')
        if value_type == 'raw':
            return raw_value
        return str(raw_value)

    def get_threshold_var(self, key, default=None, value_type=None, return_source=False):
        """threshold_list에서 key(name) 기준으로 값을 조회한다.

        - key가 없거나 변환 실패 시 default 반환
        - value_type 미지정 시 default 타입으로 자동 추론
        """
        host_var = self.get_host_var(key=key)

        if host_var:
            return host_var
            
        mapped = self.get_threshold_list_map()
        raw_value = mapped.get(key)

        has_raw = (
            key in mapped and
            raw_value is not None and
            (not isinstance(raw_value, str) or raw_value.strip() != '')
        )

        if not has_raw:
            if return_source:
                return default, 'default'
            return default

        try:
            value = self._cast_threshold_var(raw_value, default, value_type=value_type)
            if return_source:
                return value, 'api'
            return value
        except Exception:
            if return_source:
                return default, 'default'
            return default

    def get_host_vars(self):
        payload = self.ctx.get('item_payload') or {}
        host_vars = payload.get('host_vars') or {}
        return host_vars if isinstance(host_vars, dict) else {}

    def get_host_var(self, key, default=None):
        return self.get_host_vars().get(key, default)


    def _describe_rc(self, rc):
        # 쉘/SSH에서 자주 쓰이는 종료 코드를 한글 설명으로 매핑한다.
        rc_map = {
            0: '정상 종료',
            1: '일반 오류 또는 결과 없음/미일치',
            2: '잘못된 사용/실행 오류',
            126: '권한 없음 또는 실행 불가',
            127: '명령어를 찾을 수 없음',
            124: '명령 시간 초과',
            130: '사용자 인터럽트(Ctrl+C)',
            255: 'SSH/원격 실행 오류',
        }
        if rc in rc_map:
            return rc_map[rc]
        if isinstance(rc, int) and rc < 0:
            return '프로세스 비정상 종료'
        return '비정상 종료'

    def _build_history_raw_output(self):
        if not self._command_history:
            return ""
        parts = []
        for idx, item in enumerate(self._command_history, 1):
            rc = item.get('rc')
            rc_desc = self._describe_rc(rc)
            stdout = (item.get('stdout') or "").rstrip()
            stderr = (item.get('stderr') or "").rstrip()

            section = [
                f"[점검 단계 {idx}]",
                f" - 실행 명령어: {item.get('cmd', '')}",
                f" - 명령 종료코드: rc={rc} ({rc_desc})",
            ]
            # stdout/stderr가 비어 있지 않을 때만 출력 내용을 기록한다.
            if stdout and stderr:
                section.extend([
                    f" - 출력 내용(stdout): {stdout}",
                    f" - 출력 내용(stderr): {stderr}",
                ])
            elif stdout:
                section.append(f" - 출력 내용: {stdout}")
            elif stderr:
                section.append(f" - 출력 내용: {stderr}")
            parts.append("\n".join(section).rstrip())
        return "\n\n".join(parts).strip()

    def _build_virtual_raw_output(self, raw_output=None, stdout=None, stderr=None):
        """명령 이력이 없을 때도 출력 형식을 통일한다.

        - 점검 스크립트에서 `_ssh`를 통하지 않았거나
        - 로컬 계산값만 있는 경우에 fallback으로 사용한다.
        """
        out = (stdout or "").rstrip()
        err = (stderr or "").rstrip()
        raw = (raw_output or "").rstrip()

        section = [
            "[점검 단계 1]",
            " - 실행 명령어: (명령 이력 없음)",
            " - 명령 종료코드: rc=unknown (명령 이력 없음)",
        ]
        if out and err:
            section.extend([
                f" - 출력 내용(stdout): {out}",
                f" - 출력 내용(stderr): {err}",
            ])
        elif out:
            section.append(f" - 출력 내용: {out}")
        elif err:
            section.append(f" - 출력 내용: {err}")
        elif raw:
            section.append(f" - 출력 내용: {raw}")

        return "\n".join(section).rstrip()

    def _build_terminal_history_raw_output(self):
        if not self._terminal_history:
            return ""

        parts = []
        for idx, item in enumerate(self._terminal_history, 1):
            kind = str(item.get('kind') or '').strip().lower()
            raw_text = str(item.get('text') or '')
            text = '<space>' if raw_text == ' ' else raw_text.rstrip()
            section = [f"[점검 단계 {idx}]"]

            if kind == 'send':
                send_label = '자동 응답' if item.get('auto') else '터미널 송신'
                section.append(f" - {send_label}: {text}")
            elif kind == 'recv':
                recv_label = '터미널 수신(timeout)' if item.get('timeout') else '터미널 수신'
                section.append(f" - {recv_label}: {text}")
            else:
                section.append(f" - 터미널 이벤트: {text}")

            parts.append("\n".join(section).rstrip())

        return "\n\n".join(parts).strip()

    def _resolve_raw_output(self, raw_output=None, stdout=None, stderr=None):
        # 미구현 항목은 사용자 요청에 따라 문자열을 그대로 저장한다.
        if raw_output == '점검 스크립트 없음':
            return raw_output

        # 1순위: 실제 명령 이력(점검 단계 포맷)
        history_text = self._build_history_raw_output()
        terminal_text = self._build_terminal_history_raw_output()
        if history_text and terminal_text:
            return f'{history_text}\n\n{terminal_text}'.strip()
        if history_text:
            return history_text
        if terminal_text:
            return terminal_text

        # 2순위: 명령 이력이 없더라도 동일 포맷으로 fallback
        if raw_output not in (None, '') or stdout not in (None, '') or stderr not in (None, ''):
            return self._build_virtual_raw_output(raw_output=raw_output, stdout=stdout, stderr=stderr)

        # 3순위: 남길 데이터가 없어도 포맷은 통일한다.
        return self._build_virtual_raw_output()

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

    def get_elevate_for_aos(self, become_password=None):
        become_password = self.get_application_credential_value("become_password")

        if BaseCheck.PARAMIKO_ELEVATE_FAILED:
            raise RuntimeError("previous elevate failed")

        if BaseCheck.PARAMIKO_IS_ELEVATED:
            return True, "session reused"

        if not become_password:
            BaseCheck.PARAMIKO_ELEVATE_FAILED = True
            raise ValueError("become password is not defined")

        result = self._run_paramiko_commands([{'command': 'whoami'}])

        if 'root' in result[-1]['stdout']:          
            BaseCheck.PARAMIKO_IS_ELEVATED = True
            return True, 'already elevated'
        
        result = self._run_paramiko_commands([
            {'command': 'Support', 'timeout': 5, 'ignore_prompt': True, 'delay': 10},            
            {'command': 'Maintenance', 'timeout': 1, 'ignore_prompt': True},
            {'command': become_password, 'timeout': 1, 'ignore_prompt': True, 'hide_command': True},
            {'command': '/opt/Symantec/sdcssagent/IPS/sisipsoverride.sh', 'timeout': 1, 'ignore_prompt': True},
            {'command': become_password, 'timeout': 1, 'ignore_prompt': True, 'hide_command': True},
            {'command': '2', 'timeout': 3, 'ignore_prompt': True},
            {'command': become_password, 'timeout': 1, 'ignore_prompt': True, 'hide_command': True},
            {'command': '1', 'timeout': 3, 'ignore_prompt': True},
            {'command': '1', 'timeout': 5, 'ignore_prompt': True},
            {'command': 'elevate', 'timeout': 5, 'ignore_prompt': True, 'delay': 20},
            {'command': 'whoami', 'timeout': 5, 'ignore_prompt': True},
        ])

        if 'root' in result[-1]['stdout']:
            BaseCheck.PARAMIKO_IS_ELEVATED = True
            return True, 'new session'
            
        BaseCheck.PARAMIKO_ELEVATE_FAILED = True
        raise RuntimeError("failed elevate")

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
