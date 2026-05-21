# -*- coding: utf-8 -*-
"""Pure remote execution boundary helpers for BaseCheck.

The SSH/WinRM/Paramiko/Solaris execution flow stays in BaseCheck/runner; these
helpers only normalize specs or build/verify data structures with the same
legacy semantics.
"""

import re


def normalize_solaris_command_specs(command_specs):
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


def build_solaris_become_commands(config, validate_user_func):
    method = config.get('method') or 'su -'
    if method not in ('su', 'su -'):
        raise ValueError('unsupported solaris become_method: ' + str(method))

    user = validate_user_func(config.get('user') or 'root')
    password = config.get('password') or ''
    if password == '':
        raise ValueError('solaris become_password is required for ' + method)

    su_command = 'su - ' + user if method == 'su -' else 'su ' + user
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


def verify_solaris_become_result(results):
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
