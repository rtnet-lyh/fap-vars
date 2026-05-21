# -*- coding: utf-8 -*-
"""BaseCheck-facing support exports for low-risk helper behavior.

``items.common._base.BaseCheck`` keeps its public-ish methods on the class.
This module now direct re-exports canonical pure helpers where possible while
preserving the BaseCheck support layer boundary.
"""

from .utils.command_result import build_command_history_raw_output as build_history_raw_output
from .utils.command_result import build_terminal_history_raw_output
from .utils.command_result import build_virtual_raw_output
from .utils.command_result import record_command
from .utils.command_result import record_terminal_event
from .utils.command_result import resolve_raw_output
from .utils.parsing import parse_mpstat_field
from .utils.parsing import to_mb
from .utils.policy import detect_command_error
from .utils.policy import evaluate_policy_text
from .utils.policy import extract_lines
from .utils.thresholds import cast_threshold_value as cast_threshold_var

__all__ = [
    'build_history_raw_output',
    'build_terminal_history_raw_output',
    'build_virtual_raw_output',
    'cast_threshold_var',
    'detect_command_error',
    'evaluate_policy_text',
    'extract_lines',
    'parse_mpstat_field',
    'record_command',
    'record_terminal_event',
    'resolve_raw_output',
    'to_mb',
]
