# -*- coding: utf-8 -*-
"""Encoding and text normalization utilities shared by runner and BaseCheck.

These helpers intentionally preserve the previous decode order used by
runner.decode_stream_bytes() and BaseCheck.decode_paramiko_bytes().
"""

import codecs
import re

ANSI_ESCAPE_RE = re.compile(r'(?:\x1B\[[0-?]*[ -/]*[@-~]|\x1B\][^\x07]*(?:\x07|\x1B\\))')


RUNTIME_WARNING_PATTERNS = (
    re.compile(r'^(?:/bin/sh|bash): warning: setlocale: LC_ALL: cannot change locale \([^)]+\)\s*$'),
    re.compile(r'^setlocale: LC_ALL: cannot change locale \([^)]+\)\s*$'),
    re.compile(r'^bash: cannot set terminal process group \([^)]+\): Inappropriate ioctl for device\s*$'),
    re.compile(r'^bash: no job control in this shell\s*$'),
    re.compile(r'^(?:stdin: is not a tty|mesg: ttyname failed: Inappropriate ioctl for device)\s*$'),
    re.compile(r'^tput: No value for \$TERM and no -T specified\s*$'),
)


def decode_bytes(value, preferred_encodings=None):
    """Decode bytes with the legacy FAP fallback order.

    Behavior is intentionally equivalent to the previous duplicated
    implementations in runner.py and items/common/_base.py.
    """
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


def coerce_text(value):
    if value is None:
        return value
    if isinstance(value, bytes):
        return decode_bytes(value)
    return str(value)


def strip_runtime_warnings(text, coerce_text_func=None, warning_patterns=None):
    """Remove shell/runtime warning lines without changing normal output text."""
    if coerce_text_func is None:
        coerce_text_func = coerce_text

    text = coerce_text_func(text)
    if not text:
        return text

    patterns = warning_patterns or RUNTIME_WARNING_PATTERNS
    cleaned_lines = []
    for line in str(text).splitlines():
        stripped = line.strip()
        if any(pattern.match(stripped) for pattern in patterns):
            continue
        cleaned_lines.append(line)

    result = '\n'.join(cleaned_lines)
    if text.endswith('\n') and result:
        result += '\n'
    return result


def normalize_terminal_text(text, ansi_escape_re=None):
    normalized = str(text or '').replace('\r\n', '\n').replace('\r', '\n')
    return (ansi_escape_re or ANSI_ESCAPE_RE).sub('', normalized)
