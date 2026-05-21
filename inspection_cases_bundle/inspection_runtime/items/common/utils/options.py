# -*- coding: utf-8 -*-
"""Option and parser normalization utilities shared by runner and BaseCheck.

These helpers intentionally preserve the legacy parsing semantics from
runner.py and items/common/_base.py. Call sites keep their existing wrapper
names for compatibility with case scripts and result formatting.
"""

TRUTHY_VALUES = ('1', 'true', 'y', 'yes', 'on')
FALSY_VALUES = ('0', 'false', 'n', 'no', 'off')


def is_truthy_value(value):
    """Return True only for legacy truthy values.

    This matches runner.is_truthy() and threshold bool casting behavior:
    bool values are preserved, truthy strings are true, everything else is false.
    """
    if isinstance(value, bool):
        return value
    return str(value or '').strip().lower() in TRUTHY_VALUES


def parse_bool_option(value, default=False):
    """Parse loose bool options with a default for None or unknown values.

    This preserves BaseCheck._paramiko_bool_option() semantics.
    """
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in TRUTHY_VALUES:
        return True
    if text in FALSY_VALUES:
        return False
    return default


def parse_bool_strict(value):
    """Parse strict bool command options or raise ValueError.

    This preserves the legacy command-option behavior where non-bool falsey
    values such as 0 normalize to an empty string and are considered invalid.
    """
    if isinstance(value, bool):
        return value
    text = str(value or '').strip().lower()
    if text in TRUTHY_VALUES:
        return True
    if text in FALSY_VALUES:
        return False
    raise ValueError(f'invalid bool option: {value}')


def normalize_spaced_lower(value):
    """Strip, lowercase, and collapse whitespace using legacy become parsing."""
    return ' '.join(str(value or '').strip().lower().split())


def normalize_csv_tuple(values):
    """Normalize comma-separated or iterable values into a non-empty tuple."""
    if isinstance(values, str):
        values = values.split(',')
    return tuple(
        text
        for text in (str(value or '').strip() for value in (values or ()))
        if text
    )


def append_unique_preserve_order(base_values, extra_values):
    """Append missing values while preserving legacy order."""
    merged = list(base_values or ())
    for value in extra_values or ():
        if value not in merged:
            merged.append(value)
    return tuple(merged)


def threshold_list_to_map(threshold_list):
    """Convert item_payload.threshold_list into a {name: value1} mapping."""
    mapped = {}
    if isinstance(threshold_list, list):
        for item in threshold_list:
            if not isinstance(item, dict):
                continue
            name = str(item.get('name', '')).strip()
            if not name:
                continue
            mapped[name] = item.get('value1')
    return mapped


def build_paramiko_options_from_object(source):
    """Build the BaseCheck Paramiko options dict from class/instance attrs.

    The attribute names and defaults intentionally match the previous
    BaseCheck._paramiko_options() implementation.
    """
    return {
        'profile': getattr(source, 'PARAMIKO_PROFILE', 'generic_network'),
        'auth_method': getattr(source, 'PARAMIKO_AUTH_METHOD', 'auto'),
        'key_filename': getattr(source, 'PARAMIKO_KEY_FILENAME', '~/.ssh/id_rsa.pub'),
        'private_key': getattr(source, 'PARAMIKO_PRIVATE_KEY', None),
        'private_key_passphrase': getattr(source, 'PARAMIKO_PRIVATE_KEY_PASSPHRASE', None),
        'allow_agent': getattr(source, 'PARAMIKO_ALLOW_AGENT', False),
        'look_for_keys': getattr(source, 'PARAMIKO_LOOK_FOR_KEYS', False),
        'timeout_sec': getattr(source, 'PARAMIKO_TIMEOUT_SEC', 10),
        'banner_timeout_sec': getattr(source, 'PARAMIKO_BANNER_TIMEOUT_SEC', 10),
        'auth_timeout_sec': getattr(source, 'PARAMIKO_AUTH_TIMEOUT_SEC', 10),
        'read_timeout_sec': getattr(source, 'PARAMIKO_READ_TIMEOUT_SEC', 0.5),
        'probe_prompt': getattr(source, 'PARAMIKO_PROBE_PROMPT', True),
        'continue_on_timeout': getattr(source, 'PARAMIKO_CONTINUE_ON_TIMEOUT', False),
    }
