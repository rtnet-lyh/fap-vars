# -*- coding: utf-8 -*-
"""Pure text policy and command-error classification helpers.

The functions in this module are shared by BaseCheck-facing wrappers and
runner/runtime result handling.  They are intentionally free of BaseCheck,
runner, logger, and result-object state.
"""

import re


COMMAND_ERROR_PATTERNS = (
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
)

CONNECTION_ERROR_MARKERS = (
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


def evaluate_policy_text(mode, text, rule, rc=None):
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


def extract_lines(text, pattern):
    return [ln.strip() for ln in (text or '').splitlines() if re.search(pattern, ln, re.IGNORECASE)]


def detect_command_error(*texts, extra_patterns=None):
    patterns = list(COMMAND_ERROR_PATTERNS)
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


def is_not_applicable(rc, err):
    text = (err or '').strip()
    if rc in (901, 902):
        return True
    if 'WINRM_UNAVAILABLE' in text or 'WINRM_EXEC_ERROR' in text:
        return True
    return False


def is_connection_error(rc, err):
    text = (err or '').strip().lower()
    if rc in (255, 901, 902):
        return True
    return any(marker in text for marker in CONNECTION_ERROR_MARKERS)
