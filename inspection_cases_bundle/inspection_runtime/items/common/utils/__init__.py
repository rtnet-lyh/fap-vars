# -*- coding: utf-8 -*-
"""Stable common utility exports.

The implementation modules under :mod:`items.common.utils` contain both public
shared helpers and low-level BaseCheck implementation helpers.  This package
root intentionally re-exports only broadly reusable, stable helpers.  Internal
helpers such as command-result builders, Paramiko session-key builders, prompt
matching, and Solaris execution validators should be imported from their
specific modules by compatibility wrappers.
"""

from .encoding import (
    coerce_text,
    decode_bytes,
    normalize_terminal_text,
    strip_runtime_warnings,
)
from .credentials import (
    credential_data_or_empty,
    normalize_credential_key,
    preferred_credential_value,
    select_application_credential,
)
from .become import (
    normalize_become_method,
    parse_unix_id_uid,
    validate_become_user,
)
from .paramiko_config import (
    load_paramiko_private_key,
    paramiko_auth_attempts,
)
from .options import (
    FALSY_VALUES,
    TRUTHY_VALUES,
    is_truthy_value,
    parse_bool_option,
    parse_bool_strict,
)
from .thresholds import (
    cast_threshold_value,
    get_threshold_value,
)

__all__ = [
    'coerce_text',
    'decode_bytes',
    'normalize_terminal_text',
    'strip_runtime_warnings',
    'credential_data_or_empty',
    'normalize_credential_key',
    'preferred_credential_value',
    'select_application_credential',
    'normalize_become_method',
    'parse_unix_id_uid',
    'validate_become_user',
    'load_paramiko_private_key',
    'paramiko_auth_attempts',
    'FALSY_VALUES',
    'TRUTHY_VALUES',
    'is_truthy_value',
    'parse_bool_option',
    'parse_bool_strict',
    'cast_threshold_value',
    'get_threshold_value',
]
