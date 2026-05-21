# -*- coding: utf-8 -*-
"""Compatibility policy metadata for ``items.common._base.BaseCheck``.

The constants in this module are data-only guardrails for maintenance and
validation.  They do not execute checks or alter runtime behavior.
"""

BASECHECK_PUBLIC_METHODS = {
    'run',
    'ok',
    'warn',
    'fail',
    'not_applicable',
    'get_threshold_var',
    'get_threshold_list_map',
    'get_application_credential',
    'get_connection_credential',
    'get_connection_value',
    'get_application_credential_value',
    'get_connection_credential_data',
    'get_application_credential_data',
    'get_host_vars',
    'get_host_var',
}

BASECHECK_PUBLICISH_PRIVATE_METHODS = {
    '_ssh',
    '_run_paramiko_commands',
    '_run_solaris_commands',
    '_run_ps',
    '_open_paramiko_client',
    '_paramiko_options',
    '_detect_command_error',
    '_is_connection_error',
    '_is_not_applicable',
    '_record_command',
    '_evaluate_policy_text',
    '_extract_lines',
    '_to_mb',
    '_parse_mpstat_field',
}

BASECHECK_COMMAND_EXECUTION_METHODS = {
    '_ssh',
    '_run_paramiko_commands',
    '_run_solaris_commands',
    '_run_ps',
}

BASECHECK_PARAMIKO_METHODS = {
    '_paramiko_options',
    '_resolve_paramiko_profile',
    '_open_paramiko_client',
    '_create_paramiko_session',
    '_get_paramiko_session',
    '_run_paramiko_commands',
    '_run_paramiko',
}

BASECHECK_SOLARIS_METHODS = {
    '_run_solaris_commands',
    '_build_solaris_become_commands',
    '_verify_solaris_become_result',
}

BASECHECK_WINDOWS_METHODS = {
    '_run_ps',
}

BASECHECK_RESULT_METHODS = {
    'ok',
    'warn',
    'fail',
    'not_applicable',
    '_resolve_raw_output',
    '_build_history_raw_output',
    '_build_virtual_raw_output',
    '_build_terminal_history_raw_output',
}

BASECHECK_CREDENTIAL_THRESHOLD_METHODS = {
    'get_threshold_var',
    'get_threshold_list_map',
    'get_application_credential',
    'get_connection_credential',
    'get_connection_value',
    'get_application_credential_value',
    'get_connection_credential_data',
    'get_application_credential_data',
    'get_host_vars',
    'get_host_var',
    '_cast_threshold_var',
}

BASECHECK_HELPER_SLIMMING_CANDIDATES = {
    '_evaluate_policy_text',
    '_extract_lines',
    '_detect_command_error',
    '_to_mb',
    '_parse_mpstat_field',
    '_record_command',
    '_record_terminal_event',
    '_cast_threshold_var',
    '_build_history_raw_output',
    '_build_virtual_raw_output',
    '_build_terminal_history_raw_output',
    '_resolve_raw_output',
}

HIGH_RISK_BASECHECK_METHODS = {
    '_ssh',
    '_paramiko_options',
    '_resolve_paramiko_profile',
    '_open_paramiko_client',
    '_create_paramiko_session',
    '_get_paramiko_session',
    '_run_paramiko_commands',
    '_run_paramiko',
    '_run_solaris_commands',
    '_run_ps',
    'ok',
    'warn',
    'fail',
    'not_applicable',
}

REQUIRED_BASECHECK_METHODS = (
    BASECHECK_PUBLIC_METHODS
    | BASECHECK_PUBLICISH_PRIVATE_METHODS
    | BASECHECK_COMMAND_EXECUTION_METHODS
    | BASECHECK_PARAMIKO_METHODS
    | BASECHECK_SOLARIS_METHODS
    | BASECHECK_WINDOWS_METHODS
    | BASECHECK_RESULT_METHODS
    | BASECHECK_CREDENTIAL_THRESHOLD_METHODS
)
