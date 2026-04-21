#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import codecs
import os
import re
import select
import shlex
import subprocess
import time
from dataclasses import dataclass


ANSI_ESCAPE_RE = re.compile(r'(?:\x1B\[[0-?]*[ -/]*[@-~]|\x1B\][^\x07]*(?:\x07|\x1B\\))')
DEFAULT_OPEN_TIMEOUT_SEC = 10
DEFAULT_EXPECT_TIMEOUT_SEC = 0.5
DEFAULT_SEND_TIMEOUT_SEC = 0.5


def decode_terminal_bytes(value, preferred_encodings=None):
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


def normalize_terminal_text(text):
    normalized = str(text or '')
    normalized = normalized.replace('\r\n', '\n').replace('\r', '\n')
    return ANSI_ESCAPE_RE.sub('', normalized)


@dataclass
class TerminalExpectResult:
    index: int
    pattern: str
    text: str
    match_text: str
    matched: bool = True
    timed_out: bool = False

    @property
    def body(self):
        if self.match_text and self.text.endswith(self.match_text):
            return self.text[:-len(self.match_text)]
        return self.text


@dataclass
class TerminalCommandResult:
    command: str
    output: str
    raw_output: str
    matched: bool
    timed_out: bool
    prompt: str = ''
    pattern: str = ''


DEFAULT_PASSWORD_PROMPT_PATTERNS = [r'(?:[Pp]assword|암호):\s*$']
TERMINAL_PROFILES = {
    'linux': {
        'prompt_patterns': [r'(?:^|\n)[^\n\r]*[$#]\s*$'],
        'pager_patterns': [],
        'pager_response': ' ',
        'disable_paging_commands': [],
        'privilege_command': None,
        'password_patterns': DEFAULT_PASSWORD_PROMPT_PATTERNS,
    },
    'cisco_ios': {
        'prompt_patterns': [r'(?:^|\n)[^\n\r]+[>#]\s*$', r'[>#]\s*$'],
        'pager_patterns': [r'--More--', r'--More--\s*$', r'More:\s*<space>'],
        'pager_response': ' ',
        'disable_paging_commands': ['terminal length 0'],
        'privilege_command': 'enable',
        'password_patterns': DEFAULT_PASSWORD_PROMPT_PATTERNS,
    },
    'junos': {
        'prompt_patterns': [r'(?:^|\n)[^\n\r]+[>#]\s*$', r'[>#]\s*$'],
        'pager_patterns': [r'---\(more[^\)]*\)---', r'--- more ---', r'--More--'],
        'pager_response': ' ',
        'disable_paging_commands': ['set cli screen-length 0'],
        'privilege_command': None,
        'password_patterns': DEFAULT_PASSWORD_PROMPT_PATTERNS,
    },
    'generic_network': {
        'prompt_patterns': [r'(?:^|\n)[^\n\r]{1,120}[>#]\s*$', r'[>#]\s*$', r'\]\s*$'],
        'pager_patterns': [r'--More--', r'--- more ---', r'Press any key', r'More:\s*<space>'],
        'pager_response': ' ',
        'disable_paging_commands': [],
        'privilege_command': None,
        'password_patterns': DEFAULT_PASSWORD_PROMPT_PATTERNS,
    },
}


class SubprocessSshTerminalTransport:
    def __init__(self, process, preferred_encodings=None):
        self.process = process
        self.preferred_encodings = list(preferred_encodings or [])
        self.closed = False

    @classmethod
    def open(
        cls,
        host,
        port,
        user,
        password,
        ssh_options,
        open_timeout_sec=DEFAULT_OPEN_TIMEOUT_SEC,
        preferred_encodings=None,
    ):
        import shutil

        base_cmd = ['ssh', '-tt', '-p', str(port)]
        if ssh_options:
            base_cmd += shlex.split(str(ssh_options))
        target = f'{user}@{host}' if user else host
        base_cmd.append(target)
        if password:
            sshpass = shutil.which('sshpass')
            if not sshpass:
                raise RuntimeError('sshpass not installed for password auth')
            base_cmd = [sshpass, '-p', password] + base_cmd

        process = subprocess.Popen(
            base_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=0,
        )
        transport = cls(process, preferred_encodings=preferred_encodings)

        # Wait briefly for immediate connection/setup failures.
        if open_timeout_sec and open_timeout_sec > 0:
            try:
                initial = transport.read_chunk(timeout_sec=open_timeout_sec)
            except EOFError:
                initial = ''
            if initial not in (None, ''):
                transport._prefetched = initial
            else:
                transport._prefetched = None
        else:
            transport._prefetched = None

        return transport

    def send(self, text, newline=False, redacted=False):
        del redacted
        if self.closed:
            raise EOFError('terminal is closed')
        payload = str(text or '')
        if newline:
            payload += '\n'
        if not self.process.stdin:
            raise EOFError('terminal stdin is not available')
        self.process.stdin.write(payload.encode('utf-8'))
        self.process.stdin.flush()

    def read_chunk(self, timeout_sec=None):
        if self.closed:
            return ''

        prefetched = getattr(self, '_prefetched', None)
        if prefetched is not None:
            self._prefetched = None
            return prefetched

        if not self.process.stdout:
            self.closed = True
            return ''

        wait_timeout = timeout_sec
        if wait_timeout is not None and wait_timeout < 0:
            wait_timeout = 0

        ready, _write_ready, _error_ready = select.select([self.process.stdout], [], [], wait_timeout)
        if not ready:
            return None

        chunk = os.read(self.process.stdout.fileno(), 4096)
        if chunk:
            return normalize_terminal_text(
                decode_terminal_bytes(chunk, preferred_encodings=self.preferred_encodings)
            )

        self.closed = True
        raise EOFError('terminal closed by remote host')

    def close(self):
        if self.closed:
            return
        self.closed = True
        try:
            if self.process.stdin:
                self.process.stdin.close()
        except Exception:
            pass
        try:
            self.process.terminate()
            self.process.wait(timeout=1)
        except Exception:
            try:
                self.process.kill()
            except Exception:
                pass


class TerminalSession:
    def __init__(
        self,
        transport,
        history_callback=None,
        pager_patterns=None,
        pager_response=' ',
        default_timeout_sec=DEFAULT_EXPECT_TIMEOUT_SEC,
    ):
        self.transport = transport
        self.history_callback = history_callback
        self.pager_patterns = self._compile_patterns(pager_patterns or [])
        self.pager_response = str(pager_response or '')
        self.default_timeout_sec = (
            DEFAULT_EXPECT_TIMEOUT_SEC if default_timeout_sec is None else default_timeout_sec
        )
        self.buffer = ''
        self.closed = False
        self._started = False
        self._marker_counter = 0
        self.profile = {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    def _emit_history(self, event):
        if callable(self.history_callback):
            self.history_callback(event)

    def _compile_patterns(self, patterns):
        compiled = []
        for pattern in patterns or []:
            compiled.append(re.compile(str(pattern), re.MULTILINE))
        return compiled

    def _coerce_profile(self, profile):
        if profile is None:
            return {}
        if isinstance(profile, str):
            name = profile.strip().lower().replace('-', '_')
            if name not in TERMINAL_PROFILES:
                raise ValueError(f'unknown terminal profile: {profile}')
            return dict(TERMINAL_PROFILES[name])
        if isinstance(profile, dict):
            return dict(profile)
        raise TypeError('terminal profile must be a profile name or dict')

    def use_profile(self, profile):
        resolved = self._coerce_profile(profile)
        self.profile = resolved
        self.pager_patterns = self._compile_patterns(resolved.get('pager_patterns') or [])
        self.pager_response = str(resolved.get('pager_response', ' '))
        return self

    def _profile_patterns(self, key, fallback=None):
        values = self.profile.get(key)
        if values:
            return values
        return fallback or []

    def _find_match(self, compiled_patterns):
        for idx, pattern in enumerate(compiled_patterns):
            match = pattern.search(self.buffer)
            if match:
                return idx, pattern, match
        return None

    def _consume_pager(self):
        if not self.pager_patterns:
            return False

        for pattern in self.pager_patterns:
            match = pattern.search(self.buffer)
            if not match:
                continue

            self.buffer = self.buffer[:match.start()] + self.buffer[match.end():]
            if self.pager_response:
                self.transport.send(self.pager_response, newline=False, redacted=False)
                self._emit_history({
                    'kind': 'send',
                    'text': self.pager_response,
                    'redacted': False,
                    'auto': True,
                })
            return True

        return False

    def send(self, text, redact=False):
        self._prepare_send()
        self.transport.send(text, newline=False, redacted=redact)
        self._emit_history({
            'kind': 'send',
            'text': '*****' if redact else str(text or ''),
            'redacted': bool(redact),
            'auto': False,
        })

    def sendline(self, text, redact=False):
        self._prepare_send()
        self.transport.send(text, newline=True, redacted=redact)
        time.sleep(DEFAULT_SEND_TIMEOUT_SEC)
        self._emit_history({
            'kind': 'send',
            'text': '*****' if redact else str(text or ''),
            'redacted': bool(redact),
            'auto': False,
        })

    def _prepare_send(self):
        if self._started:
            return
        self._started = True
        self.drain(emit_empty=False)

    def _build_timeout_result(self, compiled_patterns):
        consumed = self.buffer
        self.buffer = ''
        self._emit_history({
            'kind': 'recv',
            'text': consumed,
            'timeout': True,
            'patterns': [pattern.pattern for pattern in compiled_patterns],
        })
        return TerminalExpectResult(
            index=-1,
            pattern='',
            text=consumed,
            match_text='',
            matched=False,
            timed_out=True,
        )

    def expect(self, patterns, timeout_sec=None, strict=False):
        self._started = True
        compiled_patterns = self._compile_patterns(patterns)
        if not compiled_patterns:
            raise ValueError('expect patterns are required')

        timeout = self.default_timeout_sec if timeout_sec is None else timeout_sec
        deadline = None if timeout is None else (time.monotonic() + float(timeout))

        while True:
            while self._consume_pager():
                pass

            match_info = self._find_match(compiled_patterns)
            if match_info:
                idx, pattern, match = match_info
                consumed = self.buffer[:match.end()]
                self.buffer = self.buffer[match.end():]
                self._emit_history({
                    'kind': 'recv',
                    'text': consumed,
                })
                return TerminalExpectResult(
                    index=idx,
                    pattern=pattern.pattern,
                    text=consumed,
                    match_text=match.group(0),
                )

            remaining = None
            if deadline is not None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    if strict:
                        raise TimeoutError(f'terminal expect timed out. patterns={compiled_patterns}')
                    return self._build_timeout_result(compiled_patterns)

            chunk = self.transport.read_chunk(timeout_sec=remaining)
            if chunk is None:
                continue
            if chunk == '':
                self.closed = True
                raise EOFError(f'terminal closed before expected prompt was received. patterns={compiled_patterns}')
            self.buffer += normalize_terminal_text(chunk)

    def drain(self, timeout_sec=None, emit_empty=True):
        self._started = True
        timeout = self.default_timeout_sec if timeout_sec is None else timeout_sec
        deadline = None if timeout is None else (time.monotonic() + float(timeout))

        while True:
            while self._consume_pager():
                pass

            remaining = None
            if deadline is not None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break

            chunk = self.transport.read_chunk(timeout_sec=remaining)
            if chunk is None:
                break
            if chunk == '':
                self.closed = True
                break
            self.buffer += normalize_terminal_text(chunk)

        consumed = self.buffer
        self.buffer = ''
        if consumed or emit_empty:
            self._emit_history({
                'kind': 'recv',
                'text': consumed,
                'drain': True,
            })
        return consumed

    def _new_marker(self):
        self._marker_counter += 1
        return f'__FAP_TERMINAL_END_{int(time.time() * 1000)}_{self._marker_counter}__'

    def _strip_command_echo(self, command, text, strip_echo=True):
        lines = str(text or '').splitlines()
        if not strip_echo or not lines:
            return '\n'.join(lines).strip()

        command_text = str(command or '').strip()
        while lines and not lines[0].strip():
            lines = lines[1:]
        if lines and command_text:
            first_line = lines[0].strip()
            if first_line == command_text or first_line.endswith(command_text):
                lines = lines[1:]
        return '\n'.join(lines).strip()

    def run_command(
        self,
        command,
        timeout_sec=30,
        end_patterns=None,
        strip_echo=True,
        strict=False,
    ):
        patterns = end_patterns or self._profile_patterns('prompt_patterns')
        if not patterns:
            raise ValueError('run_command requires end_patterns or a profile with prompt_patterns')

        self.sendline(command)
        result = self.expect(patterns, timeout_sec=timeout_sec, strict=strict)
        output = self._strip_command_echo(command, result.body, strip_echo=strip_echo)
        return TerminalCommandResult(
            command=str(command or ''),
            output=output,
            raw_output=result.text,
            matched=result.matched,
            timed_out=result.timed_out,
            prompt=result.match_text,
            pattern=result.pattern,
        )

    def run_until_marker(
        self,
        command,
        timeout_sec=30,
        marker=None,
        marker_command=None,
        strip_echo=True,
        strict=False,
    ):
        marker_text = marker or self._new_marker()
        actual_marker_command = marker_command or f'printf "\\n{marker_text}\\n"'
        actual_command = f'{command}; {actual_marker_command}'
        marker_pattern = r'(?:^|\n)' + re.escape(marker_text) + r'\s*$'
        result = self.run_command(
            actual_command,
            timeout_sec=timeout_sec,
            end_patterns=[marker_pattern],
            strip_echo=strip_echo,
            strict=strict,
        )
        output = result.output
        if marker_text in output:
            output = output.split(marker_text, 1)[0].rstrip()
        result.output = output
        return result

    def run_su_command(
        self,
        command,
        password,
        user='root',
        timeout_sec=30,
        password_patterns=None,
        marker=None,
    ):
        marker_text = marker or self._new_marker()
        command_with_marker = f'{command}; printf "\\n{marker_text}\\n"'
        su_command = 'su - {user} -c {command}'.format(
            user=shlex.quote(str(user or 'root')),
            command=shlex.quote(command_with_marker),
        )

        self.sendline(su_command)
        self.expect(password_patterns or DEFAULT_PASSWORD_PROMPT_PATTERNS)
        self.sendline(password, redact=True)
        marker_pattern = r'(?:^|\n)' + re.escape(marker_text) + r'\s*$'
        result = self.expect([marker_pattern], timeout_sec=timeout_sec)
        output = result.body
        if marker_text in output:
            output = output.split(marker_text, 1)[0]
        return TerminalCommandResult(
            command=str(command or ''),
            output=output.strip(),
            raw_output=result.text,
            matched=result.matched,
            timed_out=result.timed_out,
            prompt=result.match_text,
            pattern=result.pattern,
        )

    def enter_privilege(self, password=None, timeout_sec=5):
        privilege_command = self.profile.get('privilege_command')
        prompt_patterns = self._profile_patterns('prompt_patterns')
        if not privilege_command or not prompt_patterns:
            return False

        prompt = self.expect(prompt_patterns, timeout_sec=timeout_sec)
        if prompt.matched and str(prompt.match_text or '').strip().endswith('#'):
            return False

        self.sendline(privilege_command)
        password_patterns = self._profile_patterns('password_patterns', DEFAULT_PASSWORD_PROMPT_PATTERNS)
        result = self.expect(list(password_patterns) + list(prompt_patterns), timeout_sec=timeout_sec)
        if result.matched and result.index < len(password_patterns):
            if password in (None, ''):
                raise ValueError('privilege password is required')
            self.sendline(password, redact=True)
            self.expect(prompt_patterns, timeout_sec=timeout_sec)
        return True

    def disable_paging(self, timeout_sec=5):
        outputs = []
        for command in self.profile.get('disable_paging_commands') or []:
            outputs.append(self.run_command(command, timeout_sec=timeout_sec))
        return outputs

    def run_steps(self, steps, default_timeout_sec=DEFAULT_EXPECT_TIMEOUT_SEC):
        results = []
        for step in steps or []:
            action = str(step.get('action') or '').strip().lower()
            timeout_sec = step.get('timeout_sec', default_timeout_sec)
            if action in ('send', 'sendline'):
                self.sendline(step.get('text') or step.get('command') or '', redact=bool(step.get('redact')))
                results.append(None)
            elif action == 'expect':
                results.append(self.expect(step.get('patterns') or [], timeout_sec=timeout_sec))
            elif action == 'drain':
                results.append(self.drain(timeout_sec=timeout_sec))
            elif action == 'run':
                results.append(self.run_command(step.get('command') or '', timeout_sec=timeout_sec))
            else:
                raise ValueError(f'unsupported terminal step action: {action}')
        return results

    def run(self, command, expect_patterns, timeout_sec=None, redact=False, strip_command_echo=True, strict=False):
        self.sendline(command, redact=redact)
        result = self.expect(expect_patterns, timeout_sec=timeout_sec, strict=strict)
        output = result.body
        lines = output.splitlines()
        if strip_command_echo and lines:
            first_line = lines[0].strip()
            if first_line == str(command or '').strip():
                lines = lines[1:]
        return '\n'.join(lines).strip()

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.transport.close()
