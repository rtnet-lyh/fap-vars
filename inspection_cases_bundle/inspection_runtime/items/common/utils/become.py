# -*- coding: utf-8 -*-
"""Small, side-effect-free helpers for become/su/sudo normalization.

These helpers intentionally do not build shell commands, perform credential
lookup, interact with terminal prompts, or alter Paramiko session behavior.
"""

import re

from .options import normalize_spaced_lower

BECOME_USER_RE = re.compile(r'^[A-Za-z0-9_.-]+$')
UNIX_ID_UID_RE = re.compile(r'(?:^|\s)uid=(\d+)(?:\(([^)]*)\))?')


def normalize_become_method(value):
    """Normalize a become method name using the existing whitespace/lower rule."""
    return normalize_spaced_lower(value)


def validate_become_user(value, error_prefix='invalid become_user'):
    """Normalize and validate a become user name.

    The default user remains root. Error text is kept caller-controlled so
    existing wrappers can preserve their exact messages.
    """
    text = str(value or 'root').strip() or 'root'
    if not BECOME_USER_RE.match(text):
        raise ValueError(str(error_prefix) + ': ' + text)
    return text


def parse_unix_id_uid(output, missing_uid=None):
    """Parse uid/name from Unix `id` output.

    ``missing_uid`` preserves legacy caller differences: runner returns
    ``(None, '')`` on parse miss, while BaseCheck returns ``('', '')``.
    """
    match = UNIX_ID_UID_RE.search(str(output or ''))
    if not match:
        return missing_uid, ''
    return match.group(1), match.group(2) or ''
