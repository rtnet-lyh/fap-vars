# -*- coding: utf-8 -*-
"""SSH timeout and executor adapter helpers for inspection runner.

This module intentionally contains only small helpers extracted from
``runner.py``. Keep timeout coercion, executor signature handling, and SSH
option defaulting behavior compatible with the runner wrappers.
"""

import inspect

DEFAULT_SSH_COMMAND_TIMEOUT_SEC = 600


def normalize_ssh_command_timeout_sec(value, default=DEFAULT_SSH_COMMAND_TIMEOUT_SEC):
    try:
        resolved = int(str(value).strip())
    except Exception:
        resolved = int(default)
    if resolved <= 0:
        resolved = int(default)
    return resolved


def resolve_ssh_command_timeout_sec(mod, default=DEFAULT_SSH_COMMAND_TIMEOUT_SEC):
    timeout_value = getattr(mod, 'SSH_COMMAND_TIMEOUT_SEC', None)
    if timeout_value is None and hasattr(mod, 'CHECK_CLASS'):
        timeout_value = getattr(mod.CHECK_CLASS, 'SSH_COMMAND_TIMEOUT_SEC', None)
    return normalize_ssh_command_timeout_sec(timeout_value, default)


def executor_accepts_timeout_arg(executor):
    try:
        params = inspect.signature(executor).parameters.values()
    except (TypeError, ValueError):
        return True

    positional_count = 0
    for param in params:
        if param.kind == inspect.Parameter.VAR_POSITIONAL:
            return True
        if param.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD):
            positional_count += 1
    return positional_count >= 7


def call_ssh_executor(executor, cmd, host, port, user, password, ssh_options, timeout_sec):
    if executor_accepts_timeout_arg(executor):
        return executor(cmd, host, port, user, password, ssh_options, timeout_sec)
    return executor(cmd, host, port, user, password, ssh_options)


def ensure_ssh_options_defaults(ssh_options):
    text = (ssh_options or '').strip()
    required = [
        '-o ConnectTimeout=3',
        '-o ConnectionAttempts=1',
    ]
    for opt in required:
        if opt not in text:
            text = f'{text} {opt}'.strip()
    return text
