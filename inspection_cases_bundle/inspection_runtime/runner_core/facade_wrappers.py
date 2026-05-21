"""Public helper exports for the ``runner.py`` compatibility facade.

``runner.py`` imports low-risk helper symbols from this module so callers can
continue to use ``runner.<helper>(...)`` without keeping thin delegation
functions in the facade.  Execution- and monkeypatch-sensitive wrappers remain
as real functions in ``runner.py``.
"""

from items.common.utils.become import normalize_become_method
from items.common.utils.encoding import coerce_text
from items.common.utils.encoding import decode_bytes as decode_stream_bytes
from items.common.utils.options import is_truthy_value as is_truthy
from runner_core.connection_policy import flatten_credentials
from runner_core.connection_policy import get_connection_method
from runner_core.connection_policy import get_credential_data
from runner_core.connection_policy import get_preferred_credential_value
from runner_core.connection_policy import is_network_item
from runner_core.connection_policy import needs_host_connection
from runner_core.connection_policy import normalize_credential_key
from runner_core.connection_policy import resolve_connection_values
from runner_core.connection_policy import select_application_credential
from runner_core.connection_policy import select_connection_credential
from runner_core.context import build_item_base_context
from runner_core.context import build_paramiko_ssh_blocker
from runner_core.item_loading import APPLICATION_NAME_ALIASES
from runner_core.item_loading import COMMON_TOKEN
from runner_core.item_loading import build_db_module_name
from runner_core.item_loading import build_module_lookup_key
from runner_core.item_loading import format_exception_only_text
from runner_core.item_loading import get_inline_script_text
from runner_core.item_loading import get_module_lookup_key
from runner_core.item_loading import infer_item_descriptor
from runner_core.item_loading import iter_module_candidates
from runner_core.item_loading import load_available_items
from runner_core.item_loading import load_db_item_module
from runner_core.item_loading import load_item_module
from runner_core.item_loading import normalize_application_token
from runner_core.item_loading import resolve_item_module
from runner_core.item_loading import resolve_runtime_item_module
from runner_core.item_loading import sanitize_identifier
from runner_core.paramiko import build_paramiko_connect_kwargs
from runner_core.paramiko import get_check_attr
from runner_core.paramiko import load_paramiko_private_key
from runner_core.paramiko import parse_unix_id_uid
from runner_core.paramiko import resolve_paramiko_options
from runner_core.payload import build_lookup_payload
from runner_core.payload import normalize_item
from runner_core.payload import sanitize_item_payload
from runner_core.precheck import build_become_precheck_command
from runner_core.precheck import build_become_precheck_request
from runner_core.precheck import format_precheck_error
from runner_core.remote import POWERSHELL_UTF8_PREFIX
from runner_core.remote import strip_runtime_warnings
from runner_core.remote_exec import build_no_runner_result
from runner_core.remote_exec import build_ssh_adapter
from runner_core.remote_exec import build_winrm_ssh_adapter
from runner_core.results import build_become_precheck_fail_result
from runner_core.results import build_exec_error_result
from runner_core.results import build_missing_item_result
from runner_core.results import build_precheck_fail_result
from runner_core.results import build_runner_output
from runner_core.results import summarize_result
from runner_core.ssh_options import call_ssh_executor
from runner_core.ssh_options import ensure_ssh_options_defaults
from runner_core.ssh_options import executor_accepts_timeout_arg
from runner_core.ssh_options import normalize_ssh_command_timeout_sec
from runner_core.ssh_options import resolve_ssh_command_timeout_sec
from runner_core.winrm_options import build_winrm_options
from runner_core.winrm_options import get_winrm_shell

__all__ = [
    'APPLICATION_NAME_ALIASES',
    'COMMON_TOKEN',
    'POWERSHELL_UTF8_PREFIX',
    'build_become_precheck_command',
    'build_become_precheck_fail_result',
    'build_become_precheck_request',
    'build_db_module_name',
    'build_exec_error_result',
    'build_item_base_context',
    'build_lookup_payload',
    'build_missing_item_result',
    'build_module_lookup_key',
    'build_no_runner_result',
    'build_paramiko_connect_kwargs',
    'build_paramiko_ssh_blocker',
    'build_precheck_fail_result',
    'build_runner_output',
    'build_ssh_adapter',
    'build_winrm_options',
    'build_winrm_ssh_adapter',
    'call_ssh_executor',
    'coerce_text',
    'decode_stream_bytes',
    'ensure_ssh_options_defaults',
    'executor_accepts_timeout_arg',
    'flatten_credentials',
    'format_exception_only_text',
    'format_precheck_error',
    'get_check_attr',
    'get_connection_method',
    'get_credential_data',
    'get_inline_script_text',
    'get_module_lookup_key',
    'get_preferred_credential_value',
    'get_winrm_shell',
    'infer_item_descriptor',
    'is_network_item',
    'is_truthy',
    'iter_module_candidates',
    'load_available_items',
    'load_db_item_module',
    'load_item_module',
    'load_paramiko_private_key',
    'needs_host_connection',
    'normalize_application_token',
    'normalize_become_method',
    'normalize_credential_key',
    'normalize_item',
    'normalize_ssh_command_timeout_sec',
    'parse_unix_id_uid',
    'resolve_connection_values',
    'resolve_item_module',
    'resolve_paramiko_options',
    'resolve_runtime_item_module',
    'resolve_ssh_command_timeout_sec',
    'sanitize_identifier',
    'sanitize_item_payload',
    'select_application_credential',
    'select_connection_credential',
    'strip_runtime_warnings',
    'summarize_result',
]
