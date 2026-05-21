#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import sys
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ITEMS_DIR = os.path.join(BASE_DIR, 'items')
# items 패키지를 import할 수 있도록 BASE_DIR를 sys.path에 추가한다.
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from runner_core.facade_wrappers import (
    APPLICATION_NAME_ALIASES,
    COMMON_TOKEN,
    POWERSHELL_UTF8_PREFIX,
    build_become_precheck_command,
    build_become_precheck_request,
    build_db_module_name,
    build_exec_error_result,
    build_item_base_context,
    build_lookup_payload,
    build_missing_item_result,
    build_module_lookup_key,
    build_no_runner_result,
    build_paramiko_connect_kwargs,
    build_paramiko_ssh_blocker,
    build_precheck_fail_result,
    build_become_precheck_fail_result,
    build_runner_output,
    build_ssh_adapter,
    build_winrm_options,
    build_winrm_ssh_adapter,
    call_ssh_executor,
    coerce_text,
    decode_stream_bytes,
    ensure_ssh_options_defaults,
    executor_accepts_timeout_arg,
    flatten_credentials,
    format_exception_only_text,
    format_precheck_error,
    get_check_attr,
    get_connection_method,
    get_credential_data,
    get_inline_script_text,
    get_module_lookup_key,
    get_preferred_credential_value,
    get_winrm_shell,
    infer_item_descriptor,
    is_network_item,
    is_truthy,
    iter_module_candidates,
    load_available_items,
    load_db_item_module,
    load_item_module,
    load_paramiko_private_key,
    needs_host_connection,
    normalize_application_token,
    normalize_become_method,
    normalize_credential_key,
    normalize_item,
    normalize_ssh_command_timeout_sec,
    parse_unix_id_uid,
    resolve_connection_values,
    resolve_item_module,
    resolve_paramiko_options,
    resolve_runtime_item_module,
    resolve_ssh_command_timeout_sec,
    sanitize_identifier,
    sanitize_item_payload,
    select_application_credential,
    select_connection_credential,
    strip_runtime_warnings,
    summarize_result,
)
from runner_core import item_execution as _item_execution
from runner_core import logging as _logging_core
from runner_core import paramiko as _paramiko_core
from runner_core import precheck as _precheck
from runner_core import remote_exec as _remote_exec

_init_logger = _logging_core.init_logger
_log_item_result_summary = _logging_core.log_item_result_summary
_log_result_json = _logging_core.log_result_json
_log_item_start = _logging_core.log_item_start
_log_runner_terminated = _logging_core.log_runner_terminated

_run_host_precheck_for_method = _precheck.run_host_precheck_for_method
_run_host_precheck_loop = _precheck.run_host_precheck_loop
_run_become_precheck_loop = _precheck.run_become_precheck_loop
_run_become_precheck_for_request = _precheck.run_become_precheck_for_request

_run_paramiko_precheck = _paramiko_core.run_paramiko_precheck
_run_paramiko_exec_command = _paramiko_core.run_paramiko_exec_command
_run_paramiko_su_precheck = _paramiko_core.run_paramiko_su_precheck

_ItemPrecheckGateDeps = _item_execution.ItemPrecheckGateDeps
_ItemExecutionDispatchDeps = _item_execution.ItemExecutionDispatchDeps
_ItemExecutionContext = _item_execution.ItemExecutionContext
_ItemExecutionRuntime = _item_execution.ItemExecutionRuntime
_ItemExecutionLoopContext = _item_execution.ItemExecutionLoopContext
_ItemExecutionLoopRuntime = _item_execution.ItemExecutionLoopRuntime
_ItemExecutionDeps = _item_execution.ItemExecutionDeps
_run_module_entrypoint = _item_execution.run_module_entrypoint
_evaluate_item_precheck_gate = _item_execution.evaluate_item_precheck_gate
_execute_item_after_precheck_gate = _item_execution.execute_item_after_precheck_gate
_run_item_execution_loop = _item_execution.run_item_execution_loop

_default_winrm_session = _remote_exec._winrm_session
_run_ssh = _remote_exec.run_ssh
_run_winrm = _remote_exec.run_winrm
_run_no_ssh = _remote_exec.run_no_ssh
_run_shell_item = _remote_exec.run_shell_item
_call_module_run = _remote_exec.call_module_run

DEFAULT_SSH_OPTIONS = (
    '-o StrictHostKeyChecking=no '
    '-o UserKnownHostsFile=/dev/null '
    '-o LogLevel=ERROR '
    '-o ControlMaster=auto '
    '-o ControlPersist=120s '
    '-o ControlPath=/tmp/fap_ssh_mux_%r@%h:%p'
)
DEFAULT_SSH_COMMAND_TIMEOUT_SEC = 600
SSH_COMMAND_TIMEOUT_RC = 124
SUPPORTED_BECOME_PRECHECK_METHODS = ('sudo', 'su', 'su -')

def run_host_precheck_for_method(
    method,
    mod,
    host,
    connection_values,
    ssh_options,
    winrm_options,
    winrm_executor,
    ssh_executor,
    paramiko_client_factory,
):
    return _run_host_precheck_for_method(
        method,
        mod,
        host,
        connection_values,
        ssh_options,
        winrm_options,
        winrm_executor,
        ssh_executor,
        paramiko_client_factory,
        build_winrm_options,
        run_paramiko_precheck,
        resolve_paramiko_options,
        call_ssh_executor,
        DEFAULT_SSH_COMMAND_TIMEOUT_SEC,
    )

def run_host_precheck_loop(
    items,
    available,
    logger,
    credentials,
    host,
    port,
    user,
    password,
    ssh_options,
    winrm_options,
    winrm_executor,
    ssh_executor,
    paramiko_client_factory,
):
    return _run_host_precheck_loop(
        items,
        available,
        logger,
        credentials,
        host,
        port,
        user,
        password,
        ssh_options,
        winrm_options,
        winrm_executor,
        ssh_executor,
        paramiko_client_factory,
        normalize_item_func=normalize_item,
        build_lookup_payload_func=build_lookup_payload,
        resolve_runtime_item_module_func=resolve_runtime_item_module,
        needs_host_connection_func=needs_host_connection,
        get_connection_method_func=get_connection_method,
        select_connection_credential_func=select_connection_credential,
        resolve_connection_values_func=resolve_connection_values,
        run_host_precheck_for_method_func=run_host_precheck_for_method,
        format_precheck_error_func=format_precheck_error,
        common_token=COMMON_TOKEN,
    )

def run_become_precheck_loop(
    items,
    available,
    logger,
    credentials,
    host,
    port,
    user,
    password,
    ssh_options,
    ssh_executor,
    paramiko_client_factory,
    precheck_errors,
):
    return _run_become_precheck_loop(
        items,
        available,
        logger,
        credentials,
        host,
        port,
        user,
        password,
        ssh_options,
        ssh_executor,
        paramiko_client_factory,
        precheck_errors,
        normalize_item_func=normalize_item,
        build_lookup_payload_func=build_lookup_payload,
        resolve_runtime_item_module_func=resolve_runtime_item_module,
        needs_host_connection_func=needs_host_connection,
        get_connection_method_func=get_connection_method,
        select_connection_credential_func=select_connection_credential,
        resolve_connection_values_func=resolve_connection_values,
        select_application_credential_func=select_application_credential,
        build_become_precheck_request_func=build_become_precheck_request,
        run_become_precheck_for_request_func=run_become_precheck_for_request,
        format_precheck_error_func=format_precheck_error,
        common_token=COMMON_TOKEN,
    )

def run_become_precheck_for_request(
    method,
    mod,
    host,
    connection_values,
    ssh_options,
    ssh_executor,
    paramiko_client_factory,
    become_request,
):
    return _run_become_precheck_for_request(
        method,
        mod,
        host,
        connection_values,
        ssh_options,
        ssh_executor,
        paramiko_client_factory,
        become_request,
        run_paramiko_su_precheck,
        run_paramiko_exec_command,
        resolve_paramiko_options,
        call_ssh_executor,
        DEFAULT_SSH_COMMAND_TIMEOUT_SEC,
    )

def run_ssh(cmd, host, port, user, password, ssh_options, timeout_sec=None):
    return _run_ssh(
        cmd,
        host,
        port,
        user,
        password,
        ssh_options,
        timeout_sec=timeout_sec,
        normalize_timeout_func=normalize_ssh_command_timeout_sec,
        strip_runtime_warnings_func=strip_runtime_warnings,
        default_timeout_sec=DEFAULT_SSH_COMMAND_TIMEOUT_SEC,
        timeout_rc=SSH_COMMAND_TIMEOUT_RC,
    )

def run_paramiko_precheck(host, port, user, password, options, client_factory=None):
    return _run_paramiko_precheck(host, port, user, password, options, client_factory)

def run_paramiko_exec_command(host, port, user, password, options, command, client_factory=None):
    return _run_paramiko_exec_command(host, port, user, password, options, command, client_factory)

def run_paramiko_su_precheck(
    host,
    port,
    user,
    password,
    options,
    become_method,
    become_user,
    become_password,
    client_factory=None,
):
    return _run_paramiko_su_precheck(
        host,
        port,
        user,
        password,
        options,
        become_method,
        become_user,
        become_password,
        client_factory,
    )

def _winrm_session(host, port, user, password, transport, server_cert_validation, operation_timeout_sec, read_timeout_sec):
    return _default_winrm_session(
        host,
        port,
        user,
        password,
        transport,
        server_cert_validation,
        operation_timeout_sec,
        read_timeout_sec,
    )

def run_winrm(cmd, host, port, user, password, _ssh_options, winrm_options=None):
    return _run_winrm(
        cmd,
        host,
        port,
        user,
        password,
        _ssh_options,
        winrm_options,
        decode_stream_bytes_func=decode_stream_bytes,
        strip_runtime_warnings_func=strip_runtime_warnings,
        session_factory=_winrm_session,
    )

def run_no_ssh(cmd, host, port, user, password, ssh_options):
    return _run_no_ssh(cmd, host, port, user, password, ssh_options)

def run_shell_item(mod, ctx):
    return _run_shell_item(mod, ctx)

def init_logger(job_id, execution_id, host, host_id):
    return _init_logger(job_id, execution_id, host, host_id)

def log_item_result_summary(logger, code, res):
    return _log_item_result_summary(logger, code, res, summarize_result)

def log_result_json(logger, res):
    return _log_result_json(logger, res)

def log_item_start(
    logger,
    code,
    item_id,
    module_source,
    method,
    connection_credential,
    item_payload,
    module_key,
    app_credential,
):
    return _log_item_start(
        logger,
        code,
        item_id,
        module_source,
        method,
        connection_credential,
        item_payload,
        module_key,
        app_credential,
        COMMON_TOKEN,
    )

def log_runner_terminated(logger, total_count, failed_count):
    return _log_runner_terminated(logger, total_count, failed_count)

def call_module_run(mod, ctx):
    return _call_module_run(mod, ctx)

def run_module_entrypoint(mod, ctx, code, item_id):
    return _run_module_entrypoint(
        mod,
        ctx,
        code,
        item_id,
        run_shell_item_func=run_shell_item,
        call_module_run_func=call_module_run,
        build_no_runner_result_func=build_no_runner_result,
    )

def build_item_precheck_gate_deps():
    return _ItemPrecheckGateDeps(
        normalize_item_func=normalize_item,
        sanitize_item_payload_func=sanitize_item_payload,
        build_lookup_payload_func=build_lookup_payload,
        resolve_runtime_item_module_func=resolve_runtime_item_module,
        needs_host_connection_func=needs_host_connection,
        get_connection_method_func=get_connection_method,
        resolve_ssh_command_timeout_sec_func=resolve_ssh_command_timeout_sec,
        select_connection_credential_func=select_connection_credential,
        resolve_connection_values_func=resolve_connection_values,
        select_application_credential_func=select_application_credential,
        log_item_start_func=log_item_start,
        build_precheck_fail_result_func=build_precheck_fail_result,
        build_become_precheck_request_func=build_become_precheck_request,
        build_become_precheck_fail_result_func=build_become_precheck_fail_result,
    )

def evaluate_item_precheck_gate(
    item,
    available,
    logger,
    credentials,
    port,
    user,
    password,
    precheck_errors,
    become_precheck_errors,
    deps=None,
):
    return _evaluate_item_precheck_gate(
        item,
        available,
        logger,
        credentials,
        port,
        user,
        password,
        precheck_errors,
        become_precheck_errors,
        deps=deps or build_item_precheck_gate_deps(),
    )

def build_item_execution_dispatch_deps():
    return _ItemExecutionDispatchDeps(
        build_item_base_context_func=build_item_base_context,
        needs_host_connection_func=needs_host_connection,
        build_winrm_options_func=build_winrm_options,
        build_winrm_ssh_adapter_func=build_winrm_ssh_adapter,
        build_paramiko_ssh_blocker_func=build_paramiko_ssh_blocker,
        build_ssh_adapter_func=build_ssh_adapter,
        call_ssh_executor_func=call_ssh_executor,
        run_module_entrypoint_func=run_module_entrypoint,
        build_exec_error_result_func=build_exec_error_result,
    )

def execute_item_after_precheck_gate(
    mod=None,
    logger=None,
    no_ssh_executor=None,
    host=None,
    connection_values=None,
    ssh_options=None,
    thresholds=None,
    code=None,
    item_id=None,
    result_item_payload=None,
    ssh_command_timeout_sec=None,
    connection_credential=None,
    app_credential=None,
    app_credential_data=None,
    paramiko_client_factory=None,
    method=None,
    winrm_options=None,
    winrm_executor=None,
    ssh_executor=None,
    deps=None,
):
    if isinstance(mod, _ItemExecutionContext) and isinstance(logger, _ItemExecutionRuntime):
        return _execute_item_after_precheck_gate(
            mod,
            logger,
            deps=deps or build_item_execution_dispatch_deps(),
        )
    return _execute_item_after_precheck_gate(
        _ItemExecutionContext(
            mod=mod,
            logger=logger,
            code=code,
            item_id=item_id,
            result_item_payload=result_item_payload,
            method=method,
            ssh_command_timeout_sec=ssh_command_timeout_sec,
            connection_credential=connection_credential,
            app_credential=app_credential,
            app_credential_data=app_credential_data,
        ),
        _ItemExecutionRuntime(
            no_ssh_executor=no_ssh_executor,
            host=host,
            connection_values=connection_values,
            ssh_options=ssh_options,
            thresholds=thresholds,
            paramiko_client_factory=paramiko_client_factory,
            winrm_options=winrm_options,
            winrm_executor=winrm_executor,
            ssh_executor=ssh_executor,
        ),
        deps=deps or build_item_execution_dispatch_deps(),
    )

def run_item_execution_loop(
    items,
    available,
    logger,
    credentials,
    port,
    user,
    password,
    precheck_errors,
    become_precheck_errors,
    no_ssh_executor,
    host,
    ssh_options,
    thresholds,
    paramiko_client_factory,
    winrm_options,
    winrm_executor,
    ssh_executor,
    item_sleep_sec,
):
    deps = _ItemExecutionDeps(
        evaluate_item_precheck_gate_func=evaluate_item_precheck_gate,
        build_missing_item_result_func=build_missing_item_result,
        normalize_application_token_func=normalize_application_token,
        log_result_json_func=log_result_json,
        execute_item_after_precheck_gate_func=execute_item_after_precheck_gate,
        log_item_result_summary_func=log_item_result_summary,
        sleep_func=time.sleep,
        gate_deps=build_item_precheck_gate_deps(),
        dispatch_deps=build_item_execution_dispatch_deps(),
    )
    return _run_item_execution_loop(
        _ItemExecutionLoopContext(
            items=items,
            available=available,
            logger=logger,
            credentials=credentials,
            port=port,
            user=user,
            password=password,
            precheck_errors=precheck_errors,
            become_precheck_errors=become_precheck_errors,
            item_sleep_sec=item_sleep_sec,
        ),
        _ItemExecutionLoopRuntime(
            no_ssh_executor=no_ssh_executor,
            host=host,
            ssh_options=ssh_options,
            thresholds=thresholds,
            paramiko_client_factory=paramiko_client_factory,
            winrm_options=winrm_options,
            winrm_executor=winrm_executor,
            ssh_executor=ssh_executor,
        ),
        deps=deps,
    )

def execute_runner(
    payload,
    ssh_executor=None,
    winrm_executor=None,
    no_ssh_executor=None,
    paramiko_client_factory=None,
    skip_precheck=False,
    logger=None,
):
    payload = payload or {}
    items = payload.get('items') or []
    host = payload.get('host')
    host_id = payload.get('host_id')
    job_id = payload.get('job_id')
    execution_id = payload.get('execution_id')
    port = payload.get('port', 22)
    credentials = payload.get('credentials') or {}
    user = payload.get('user')
    password = payload.get('password')
    ssh_options = ensure_ssh_options_defaults(payload.get('ssh_options', DEFAULT_SSH_OPTIONS))
    thresholds = payload.get('thresholds', {})
    item_sleep_sec = payload.get('item_sleep_sec', 0.05)
    winrm_options = payload.get('winrm_options') or {}

    try:
        item_sleep_sec = float(item_sleep_sec)
    except Exception:
        item_sleep_sec = 0.05
    if item_sleep_sec < 0:
        item_sleep_sec = 0.0
    if item_sleep_sec > 5.0:
        item_sleep_sec = 5.0

    logger = logger or init_logger(job_id, execution_id, host, host_id)
    ssh_executor = ssh_executor or run_ssh
    winrm_executor = winrm_executor or run_winrm
    no_ssh_executor = no_ssh_executor or run_no_ssh

    logger.info('-----------------------------------------------')
    logger.info('### Runner started.')
    logger.info('job_id=%s execution_id=%s host_id=%s host=%s port=%s user=%s', job_id, execution_id, host_id, host, port, user or '')
    logger.info('items_count=%s', len(items))
    logger.info('item_sleep_sec=%s', item_sleep_sec)

    available, available_codes = load_available_items(logger)
    logger.info('available_items=%s available_codes=%s', len(available), len(available_codes))

    if not items:
        # items 미지정 시 전체 항목 자동 실행하지 않는다.
        # (API 조회 결과가 비어있는 host에서 오동작 방지)
        logger.info('items not provided. skip checks for this host.')

    # host는 SSH가 필요한 항목이 있을 때만 필수
    # (전체 항목이 로컬 실행이면 host 없이도 허용)
    # 필요성 판단은 항목 로드 후 수행한다.
    any_host_conn_needed = False
    for it in items:
        code, _, item_payload = normalize_item(it)
        mod, _, _, _ = resolve_runtime_item_module(available, build_lookup_payload(code, item_payload), logger)
        if mod and needs_host_connection(mod):
            any_host_conn_needed = True
            break

    if any_host_conn_needed and not host:
        logger.error('host is required for host connection items.')
        raise ValueError('host is required')

    precheck_errors = {}
    checked_methods = set()
    become_precheck_errors = {}
    checked_become_prechecks = set()
    if not skip_precheck:
        precheck_errors, checked_methods = run_host_precheck_loop(
            items,
            available,
            logger,
            credentials,
            host,
            port,
            user,
            password,
            ssh_options,
            winrm_options,
            winrm_executor,
            ssh_executor,
            paramiko_client_factory,
        )
        become_precheck_errors, checked_become_prechecks = run_become_precheck_loop(
            items,
            available,
            logger,
            credentials,
            host,
            port,
            user,
            password,
            ssh_options,
            ssh_executor,
            paramiko_client_factory,
            precheck_errors,
        )
    else:
        logger.info('host precheck skipped.')

    results = run_item_execution_loop(
        items,
        available,
        logger,
        credentials,
        port,
        user,
        password,
        precheck_errors,
        become_precheck_errors,
        no_ssh_executor,
        host,
        ssh_options,
        thresholds,
        paramiko_client_factory,
        winrm_options,
        winrm_executor,
        ssh_executor,
        item_sleep_sec,
    )

    output = build_runner_output(items, results)
    log_runner_terminated(logger, len(results), len(output['failed_items']))
    return output

def main():
    payload = json.load(sys.stdin)
    try:
        output = execute_runner(payload)
    except ValueError as exc:
        print(json.dumps({'error': str(exc)}, ensure_ascii=False))
        sys.exit(1)
    print(json.dumps(output, ensure_ascii=False))

if __name__ == '__main__':
    main()
