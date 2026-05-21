# -*- coding: utf-8 -*-
"""Pure Paramiko command/prompt helper functions.

Execution-loop behavior remains in BaseCheck. These helpers only normalize
command specs or perform small text/channel predicates used by that loop.
"""

import re


def normalize_paramiko_commands(commands, bool_option_parser):
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
                item['ignore_prompt'] = bool_option_parser(
                    command.get('ignore_prompt'),
                    option_name='ignore_prompt',
                    command_index=idx,
                )

            raw_hide_command = command.get('hide_command')
            if raw_hide_command is not None:
                item['hide_command'] = bool_option_parser(
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


def compile_paramiko_patterns(patterns):
    return [re.compile(str(pattern), re.MULTILINE) for pattern in (patterns or [])]


def paramiko_command_matches_line(command, line):
    command_text = str(command or '').strip()
    line_text = str(line or '').strip()
    if not command_text or not line_text:
        return False
    return line_text == command_text or line_text.endswith(command_text)


def redact_paramiko_command_text(text, command, display_command):
    body = str(text or '')
    command_text = str(command or '')
    masked = str(display_command or command or '')
    if not body or not command_text or command_text == masked:
        return body
    return body.replace(command_text, masked)


def extract_paramiko_prompt(text, command=None, command_matches_line_func=paramiko_command_matches_line):
    lines = str(text or '').splitlines()
    for line in reversed(lines):
        candidate = line.rstrip()
        if not candidate.strip():
            continue
        if command_matches_line_func(command, candidate):
            continue
        return candidate
    return ''


def paramiko_buffer_endswith_prompt(text, prompt):
    prompt_text = str(prompt or '').rstrip()
    if not prompt_text:
        return False
    return str(text or '').rstrip().endswith(prompt_text)


def paramiko_recv_ready(channel):
    try:
        return bool(channel.recv_ready())
    except Exception:
        return False


def paramiko_channel_closed(channel):
    return bool(getattr(channel, 'closed', False))


def paramiko_sendline(channel, text):
    channel.send(str(text or '') + '\n')
