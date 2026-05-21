# -*- coding: utf-8 -*-
"""Pure parsing and unit conversion helpers shared by runtime layers."""

import re


_SIZE_RE = re.compile(r'^([0-9]+(?:\.[0-9]+)?)([kmgt]?i?b?|)$', re.IGNORECASE)
_MPSTAT_ALL_RE = re.compile(r'(^|\s)(average:)?\s*all(\s|$)')


def to_mb(value):
    text = str(value or '').strip()
    if not text:
        return None
    match = _SIZE_RE.match(text)
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


def parse_mpstat_field(text, field_name):
    target = field_name.lower().lstrip('%')
    lines = [line.strip() for line in (text or '').splitlines() if line.strip()]
    header = None
    data = None

    for line in lines:
        lower = line.lower()
        if '%' + target in lower:
            header = re.split(r'\s+', line)
            continue
        if _MPSTAT_ALL_RE.search(lower):
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
