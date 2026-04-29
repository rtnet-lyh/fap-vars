# -*- coding: utf-8 -*-

import codecs
import io
import os
import re
import time

from .helpers import NetworkHelper, VMwareHelper, WebHelper


ANSI_ESCAPE_RE = re.compile(r'(?:\x1B\[[0-?]*[ -/]*[@-~]|\x1B\][^\x07]*(?:\x07|\x1B\\))')
DEFAULT_PASSWORD_PROMPT_PATTERNS = [r'(?:[Pp]assword|암호):\s*$']
PARAMIKO_PROFILES = {
    'generic_network': {
        'pager_patterns': [r'--More--', r'--- more ---', r'Press any key', r'More:\s*<space>'],
        'pager_response': ' ',
    },
    'linux': {
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
    normalized = str(text or '').replace('\r\n', '\n').replace('\r', '\n')
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

    def _ssh(self, cmd):
        """현재 항목의 host 컨텍스트로 명령을 1회 실행한다."""
        rc, out, err = self.ctx['ssh'](
            cmd,
            self.ctx['host'],
            self.ctx['port'],
            self.ctx['user'],
            self.ctx['password'],
            self.ctx['ssh_options'],
        )
        self._record_command(cmd, rc, out, err)
        return rc, out, err

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

    def _paramiko_sendline(self, channel, text):
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

    def _run_paramiko_commands(self, commands, profile=None, enable_mode=None, timeout_sec=None):
        """Paramiko interactive shell로 여러 CLI 명령을 한 세션에서 순차 실행한다."""
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
        client = None
        channel = None
        current_prompt = ''
        results = []

        try:
            client = self._open_paramiko_client(options)
            channel = client.invoke_shell(term='vt100', width=200, height=1000)
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

            if enable_required:
                if not current_prompt.endswith('#'):
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
                elif timed_out and ignore_prompt:
                    current_prompt = ''
                if item['rc'] != 0 and not (ignore_prompt and timed_out):
                    break
        except Exception as exc:
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

        return results

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

    def fail(self, error, message=None, stdout=None, stderr=None, raw_output=None):
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
