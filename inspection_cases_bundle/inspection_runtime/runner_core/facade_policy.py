"""Compatibility policy metadata for the public ``runner.py`` facade.

The sets in this module are intentionally data-only. They document which
symbols must remain available from ``runner.py`` even when their internal
implementation is delegated into ``runner_core`` modules.
"""

RUNNER_ENTRYPOINT_WRAPPERS = {
    "execute_runner",
    "main",
}

MONKEYPATCH_SENSITIVE_WRAPPERS = {
    "_winrm_session",
    "run_winrm",
}

PUBLIC_COMPATIBILITY_WRAPPERS = {
    "run_ssh",
    "run_no_ssh",
    "run_paramiko_precheck",
    "run_paramiko_exec_command",
    "run_paramiko_su_precheck",
    "run_host_precheck_loop",
    "run_become_precheck_loop",
    "run_item_execution_loop",
    "evaluate_item_precheck_gate",
    "execute_item_after_precheck_gate",
}

DIRECT_IMPORTED_HELPER_SYMBOLS = {
    "decode_stream_bytes",
    "coerce_text",
    "strip_runtime_warnings",
    "normalize_ssh_command_timeout_sec",
    "resolve_ssh_command_timeout_sec",
    "executor_accepts_timeout_arg",
    "call_ssh_executor",
    "load_item_module",
    "sanitize_identifier",
    "load_db_item_module",
    "get_inline_script_text",
    "format_exception_only_text",
    "normalize_application_token",
    "infer_item_descriptor",
    "get_module_lookup_key",
    "build_module_lookup_key",
    "build_db_module_name",
    "iter_module_candidates",
    "resolve_item_module",
    "resolve_runtime_item_module",
    "sanitize_item_payload",
    "normalize_item",
    "build_lookup_payload",
    "load_available_items",
    "normalize_credential_key",
    "flatten_credentials",
    "is_network_item",
    "select_connection_credential",
    "select_application_credential",
    "resolve_connection_values",
    "get_credential_data",
    "get_preferred_credential_value",
    "is_truthy",
    "normalize_become_method",
    "build_become_precheck_command",
    "build_become_precheck_request",
    "format_precheck_error",
    "get_check_attr",
    "resolve_paramiko_options",
    "load_paramiko_private_key",
    "build_paramiko_connect_kwargs",
    "parse_unix_id_uid",
    "ensure_ssh_options_defaults",
    "needs_host_connection",
    "get_connection_method",
    "get_winrm_shell",
    "build_winrm_options",
    "build_winrm_ssh_adapter",
    "build_ssh_adapter",
    "build_paramiko_ssh_blocker",
    "build_item_base_context",
    "summarize_result",
    "build_runner_output",
    "build_precheck_fail_result",
    "build_become_precheck_fail_result",
    "build_missing_item_result",
    "build_no_runner_result",
    "build_exec_error_result",
}

HIGH_RISK_DIRECT_RUNNER_WRAPPERS = (
    RUNNER_ENTRYPOINT_WRAPPERS
    | MONKEYPATCH_SENSITIVE_WRAPPERS
    | PUBLIC_COMPATIBILITY_WRAPPERS
)

REQUIRED_RUNNER_WRAPPERS = (
    RUNNER_ENTRYPOINT_WRAPPERS
    | MONKEYPATCH_SENSITIVE_WRAPPERS
    | PUBLIC_COMPATIBILITY_WRAPPERS
    | DIRECT_IMPORTED_HELPER_SYMBOLS
)

FACADE_HELPER_SYMBOLS = DIRECT_IMPORTED_HELPER_SYMBOLS
# Backward-compatible metadata name: these symbols are still public through
# runner.py, but Stage 10-5K exposes them by direct import rather than thin
# def wrappers.
FACADE_HELPER_WRAPPERS = DIRECT_IMPORTED_HELPER_SYMBOLS
FACADE_SLIMMING_CANDIDATES = DIRECT_IMPORTED_HELPER_SYMBOLS
