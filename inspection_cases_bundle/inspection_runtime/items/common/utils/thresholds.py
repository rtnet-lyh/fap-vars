# -*- coding: utf-8 -*-
"""Threshold lookup and casting helpers shared by BaseCheck.

These helpers preserve the legacy BaseCheck threshold semantics: missing,
None, and blank-string values fall back to the provided default, and casting
errors are handled by the caller.
"""

from .options import is_truthy_value


def infer_threshold_value_type(default, value_type=None):
    """Resolve the threshold value_type using BaseCheck's legacy inference."""
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

    return str(value_type).lower()


def cast_threshold_value(raw_value, default=None, value_type=None):
    """Cast a raw threshold value while preserving BaseCheck semantics."""
    value_type = infer_threshold_value_type(default, value_type=value_type)

    if value_type == 'int':
        return int(str(raw_value).strip())
    if value_type == 'float':
        return float(str(raw_value).strip())
    if value_type == 'bool':
        return is_truthy_value(raw_value)
    if value_type == 'raw':
        return raw_value
    return str(raw_value)


def has_threshold_raw_value(mapped, key):
    """Return True when the mapped threshold contains a non-empty raw value."""
    raw_value = mapped.get(key)
    return (
        key in mapped and
        raw_value is not None and
        (not isinstance(raw_value, str) or raw_value.strip() != '')
    )


def get_threshold_value(mapped, key, default=None, value_type=None, return_source=False):
    """Resolve and cast a threshold value from a precomputed mapping."""
    if not has_threshold_raw_value(mapped, key):
        if return_source:
            return default, 'default'
        return default

    try:
        value = cast_threshold_value(mapped.get(key), default, value_type=value_type)
        if return_source:
            return value, 'api'
        return value
    except Exception:
        if return_source:
            return default, 'default'
        return default
