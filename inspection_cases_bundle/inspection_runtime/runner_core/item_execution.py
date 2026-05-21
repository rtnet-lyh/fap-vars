# -*- coding: utf-8 -*-
"""Item execution helpers for inspection runner.

This module contains only small helpers extracted from ``runner.py``. Keep
entrypoint call order, fallback behavior, and exception propagation compatible
with the runner wrappers.
"""

import inspect
import json
from dataclasses import dataclass, replace


@dataclass(frozen=True)
class ItemPrecheckGateDeps:
    normalize_item_func: object
    sanitize_item_payload_func: object
    build_lookup_payload_func: object
    resolve_runtime_item_module_func: object
    needs_host_connection_func: object
    get_connection_method_func: object
    resolve_ssh_command_timeout_sec_func: object
    select_connection_credential_func: object
    resolve_connection_values_func: object
    select_application_credential_func: object
    log_item_start_func: object
    build_precheck_fail_result_func: object
    build_become_precheck_request_func: object
    build_become_precheck_fail_result_func: object


@dataclass(frozen=True)
class ItemPrecheckGateContext:
    item: object
    available: object
    logger: object
    credentials: object
    port: object
    user: object
    password: object
    precheck_errors: object
    become_precheck_errors: object


@dataclass(frozen=True)
class ItemPrecheckGateItemPayload:
    code: object
    item_id: object
    item_payload: object
    result_item_payload: object
    lookup_payload: object


@dataclass(frozen=True)
class ItemPrecheckGateState:
    item: object
    code: object
    item_id: object
    item_payload: object
    result_item_payload: object
    lookup_payload: object
    mod: object
    module_key: object
    module_source: object
    db_error: object
    method: object
    ssh_command_timeout_sec: object
    connection_credential: object
    connection_values: object
    app_credential: object
    app_credential_data: object
    become_request: object = None


@dataclass(frozen=True)
class ItemExecutionDispatchDeps:
    build_item_base_context_func: object
    needs_host_connection_func: object
    build_winrm_options_func: object
    build_winrm_ssh_adapter_func: object
    build_paramiko_ssh_blocker_func: object
    build_ssh_adapter_func: object
    call_ssh_executor_func: object
    run_module_entrypoint_func: object
    build_exec_error_result_func: object


@dataclass(frozen=True)
class ItemExecutionContext:
    mod: object
    logger: object
    code: object
    item_id: object
    result_item_payload: object
    method: object
    ssh_command_timeout_sec: object
    connection_credential: object
    app_credential: object
    app_credential_data: object


@dataclass(frozen=True)
class ItemExecutionRuntime:
    no_ssh_executor: object
    host: object
    connection_values: object
    ssh_options: object
    thresholds: object
    paramiko_client_factory: object
    winrm_options: object
    winrm_executor: object
    ssh_executor: object



@dataclass(frozen=True)
class ItemExecutionLoopContext:
    items: object
    available: object
    logger: object
    credentials: object
    port: object
    user: object
    password: object
    precheck_errors: object
    become_precheck_errors: object
    item_sleep_sec: object


@dataclass(frozen=True)
class ItemExecutionLoopRuntime:
    no_ssh_executor: object
    host: object
    ssh_options: object
    thresholds: object
    paramiko_client_factory: object
    winrm_options: object
    winrm_executor: object
    ssh_executor: object


@dataclass(frozen=True)
class ItemExecutionDeps:
    evaluate_item_precheck_gate_func: object = None
    build_missing_item_result_func: object = None
    normalize_application_token_func: object = None
    log_result_json_func: object = None
    execute_item_after_precheck_gate_func: object = None
    log_item_result_summary_func: object = None
    sleep_func: object = None
    gate_deps: object = None
    dispatch_deps: object = None


def _call_with_optional_deps(func, args, deps):
    if deps is None:
        return func(*args)
    try:
        signature = inspect.signature(func)
    except (TypeError, ValueError):
        return func(*args)
    parameters = signature.parameters
    accepts_kwargs = any(param.kind == inspect.Parameter.VAR_KEYWORD for param in parameters.values())
    if 'deps' in parameters or accepts_kwargs:
        return func(*args, deps=deps)
    return func(*args)


def call_module_run(mod, ctx):
    try:
        return mod.run(ctx)
    except TypeError:
        return mod.run()


def run_module_entrypoint(
    mod,
    ctx,
    code,
    item_id,
    run_shell_item_func,
    call_module_run_func,
    build_no_runner_result_func,
):
    item_type = getattr(mod, 'ITEM_TYPE', 'python')
    if item_type == 'shell':
        return run_shell_item_func(mod, ctx)
    if hasattr(mod, 'CHECK_CLASS'):
        return mod.CHECK_CLASS(ctx).run()
    if hasattr(mod, 'run'):
        return call_module_run_func(mod, ctx)
    return build_no_runner_result_func(code, item_id)


def _build_item_precheck_gate_deps(
    deps=None,
    normalize_item_func=None,
    sanitize_item_payload_func=None,
    build_lookup_payload_func=None,
    resolve_runtime_item_module_func=None,
    needs_host_connection_func=None,
    get_connection_method_func=None,
    resolve_ssh_command_timeout_sec_func=None,
    select_connection_credential_func=None,
    resolve_connection_values_func=None,
    select_application_credential_func=None,
    log_item_start_func=None,
    build_precheck_fail_result_func=None,
    build_become_precheck_request_func=None,
    build_become_precheck_fail_result_func=None,
):
    if deps is not None:
        return deps
    return ItemPrecheckGateDeps(
        normalize_item_func=normalize_item_func,
        sanitize_item_payload_func=sanitize_item_payload_func,
        build_lookup_payload_func=build_lookup_payload_func,
        resolve_runtime_item_module_func=resolve_runtime_item_module_func,
        needs_host_connection_func=needs_host_connection_func,
        get_connection_method_func=get_connection_method_func,
        resolve_ssh_command_timeout_sec_func=resolve_ssh_command_timeout_sec_func,
        select_connection_credential_func=select_connection_credential_func,
        resolve_connection_values_func=resolve_connection_values_func,
        select_application_credential_func=select_application_credential_func,
        log_item_start_func=log_item_start_func,
        build_precheck_fail_result_func=build_precheck_fail_result_func,
        build_become_precheck_request_func=build_become_precheck_request_func,
        build_become_precheck_fail_result_func=build_become_precheck_fail_result_func,
    )


def _build_item_precheck_gate_context(
    item,
    available,
    logger,
    credentials,
    port,
    user,
    password,
    precheck_errors,
    become_precheck_errors,
):
    if isinstance(item, ItemPrecheckGateContext):
        return item
    return ItemPrecheckGateContext(
        item=item,
        available=available,
        logger=logger,
        credentials=credentials,
        port=port,
        user=user,
        password=password,
        precheck_errors=precheck_errors,
        become_precheck_errors=become_precheck_errors,
    )


def _resolve_gate_item_payload(item, deps):
    code, item_id, item_payload = deps.normalize_item_func(item)
    result_item_payload = deps.sanitize_item_payload_func(item_payload)
    lookup_payload = deps.build_lookup_payload_func(code, item_payload)
    return ItemPrecheckGateItemPayload(
        code=code,
        item_id=item_id,
        item_payload=item_payload,
        result_item_payload=result_item_payload,
        lookup_payload=lookup_payload,
    )


def _resolve_gate_module(available, lookup_payload, logger, deps):
    return deps.resolve_runtime_item_module_func(available, lookup_payload, logger)


def _resolve_gate_method(mod, lookup_payload, deps):
    method = 'none'
    if mod and deps.needs_host_connection_func(mod):
        method = deps.get_connection_method_func(mod, lookup_payload)
    return method


def _resolve_gate_ssh_command_timeout(mod, method, deps):
    if mod and method == 'ssh':
        return deps.resolve_ssh_command_timeout_sec_func(mod)
    return None


def _resolve_gate_connection(context, method, lookup_payload, deps):
    connection_credential = deps.select_connection_credential_func(
        context.credentials,
        method,
        lookup_payload,
    )
    connection_values = deps.resolve_connection_values_func(
        context.port,
        method,
        connection_credential,
        context.user,
        context.password,
    )
    return connection_credential, connection_values


def _resolve_gate_application_credential(context, lookup_payload, deps):
    app_credential = deps.select_application_credential_func(context.credentials, lookup_payload)
    app_credential_data = {}
    if isinstance(app_credential, dict):
        app_credential_data = app_credential.get('data') or {}
    return app_credential, app_credential_data


def _resolve_item_precheck_gate_state(context, deps):
    payload = _resolve_gate_item_payload(context.item, deps)
    mod, module_key, module_source, db_error = _resolve_gate_module(
        context.available,
        payload.lookup_payload,
        context.logger,
        deps,
    )
    method = _resolve_gate_method(mod, payload.lookup_payload, deps)
    ssh_command_timeout_sec = _resolve_gate_ssh_command_timeout(mod, method, deps)
    connection_credential, connection_values = _resolve_gate_connection(
        context,
        method,
        payload.lookup_payload,
        deps,
    )
    app_credential, app_credential_data = _resolve_gate_application_credential(
        context,
        payload.lookup_payload,
        deps,
    )
    return ItemPrecheckGateState(
        item=context.item,
        code=payload.code,
        item_id=payload.item_id,
        item_payload=payload.item_payload,
        result_item_payload=payload.result_item_payload,
        lookup_payload=payload.lookup_payload,
        mod=mod,
        module_key=module_key,
        module_source=module_source,
        db_error=db_error,
        method=method,
        ssh_command_timeout_sec=ssh_command_timeout_sec,
        connection_credential=connection_credential,
        connection_values=connection_values,
        app_credential=app_credential,
        app_credential_data=app_credential_data,
    )


def _log_item_precheck_gate_start(context, state, deps):
    deps.log_item_start_func(
        context.logger,
        state.code,
        state.item_id,
        state.module_source,
        state.method,
        state.connection_credential,
        state.item_payload,
        state.module_key,
        state.app_credential,
    )


def _build_item_precheck_gate_result(state, should_skip, result, become_request):
    return {
        'should_skip': should_skip,
        'result': result,
        'item': state.item,
        'code': state.code,
        'item_id': state.item_id,
        'item_payload': state.item_payload,
        'result_item_payload': state.result_item_payload,
        'lookup_payload': state.lookup_payload,
        'mod': state.mod,
        'module_key': state.module_key,
        'module_source': state.module_source,
        'db_error': state.db_error,
        'method': state.method,
        'ssh_command_timeout_sec': state.ssh_command_timeout_sec,
        'connection_credential': state.connection_credential,
        'connection_values': state.connection_values,
        'app_credential': state.app_credential,
        'app_credential_data': state.app_credential_data,
        'become_request': become_request,
    }


def _build_host_precheck_skip_gate_result(state, err_text, deps):
    res = deps.build_precheck_fail_result_func(
        state.code,
        state.item_id,
        state.item_payload,
        state.method,
        err_text,
    )
    return _build_item_precheck_gate_result(state, True, res, None)


def _build_become_precheck_request_for_gate(state, deps):
    if not state.mod:
        return None
    return deps.build_become_precheck_request_func(
        state.method,
        state.lookup_payload,
        state.connection_values,
        state.connection_credential,
        state.app_credential,
    )


def _build_become_precheck_skip_gate_result(state, err_text, deps):
    res = deps.build_become_precheck_fail_result_func(
        state.code,
        state.item_id,
        state.item_payload,
        state.method,
        err_text,
    )
    return _build_item_precheck_gate_result(state, True, res, state.become_request)


def _build_executable_precheck_gate_result(state):
    return _build_item_precheck_gate_result(state, False, None, state.become_request)


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
    normalize_item_func=None,
    sanitize_item_payload_func=None,
    build_lookup_payload_func=None,
    resolve_runtime_item_module_func=None,
    needs_host_connection_func=None,
    get_connection_method_func=None,
    resolve_ssh_command_timeout_sec_func=None,
    select_connection_credential_func=None,
    resolve_connection_values_func=None,
    select_application_credential_func=None,
    log_item_start_func=None,
    build_precheck_fail_result_func=None,
    build_become_precheck_request_func=None,
    build_become_precheck_fail_result_func=None,
    deps=None,
):
    deps = _build_item_precheck_gate_deps(
        deps=deps,
        normalize_item_func=normalize_item_func,
        sanitize_item_payload_func=sanitize_item_payload_func,
        build_lookup_payload_func=build_lookup_payload_func,
        resolve_runtime_item_module_func=resolve_runtime_item_module_func,
        needs_host_connection_func=needs_host_connection_func,
        get_connection_method_func=get_connection_method_func,
        resolve_ssh_command_timeout_sec_func=resolve_ssh_command_timeout_sec_func,
        select_connection_credential_func=select_connection_credential_func,
        resolve_connection_values_func=resolve_connection_values_func,
        select_application_credential_func=select_application_credential_func,
        log_item_start_func=log_item_start_func,
        build_precheck_fail_result_func=build_precheck_fail_result_func,
        build_become_precheck_request_func=build_become_precheck_request_func,
        build_become_precheck_fail_result_func=build_become_precheck_fail_result_func,
    )
    context = _build_item_precheck_gate_context(
        item,
        available,
        logger,
        credentials,
        port,
        user,
        password,
        precheck_errors,
        become_precheck_errors,
    )
    state = _resolve_item_precheck_gate_state(context, deps)
    _log_item_precheck_gate_start(context, state, deps)

    if state.method in context.precheck_errors:
        return _build_host_precheck_skip_gate_result(
            state,
            context.precheck_errors[state.method],
            deps,
        )

    become_request = _build_become_precheck_request_for_gate(state, deps)
    state = replace(state, become_request=become_request)
    if become_request and become_request['key'] in context.become_precheck_errors:
        return _build_become_precheck_skip_gate_result(
            state,
            context.become_precheck_errors[become_request['key']],
            deps,
        )

    return _build_executable_precheck_gate_result(state)

def _execute_item_after_precheck_gate_with_context(execution_context, runtime_context, deps):
    ctx = deps.build_item_base_context_func(
        runtime_context.no_ssh_executor,
        runtime_context.host,
        runtime_context.connection_values,
        runtime_context.ssh_options,
        runtime_context.thresholds,
        execution_context.code,
        execution_context.item_id,
        execution_context.result_item_payload,
        execution_context.ssh_command_timeout_sec,
        execution_context.connection_credential,
        execution_context.app_credential,
        execution_context.app_credential_data,
        runtime_context.paramiko_client_factory,
    )
    execution_context.logger.info("created ctx:\n%s", json.dumps(ctx, ensure_ascii=False, indent=2, default=str))
    if deps.needs_host_connection_func(execution_context.mod):
        ctx['connection_method'] = execution_context.method
        if execution_context.method == 'winrm':
            wr_opts = deps.build_winrm_options_func(execution_context.mod, runtime_context.winrm_options)
            ctx['ssh'] = deps.build_winrm_ssh_adapter_func(runtime_context.winrm_executor, wr_opts)
        elif execution_context.method == 'paramiko':
            ctx['ssh'] = deps.build_paramiko_ssh_blocker_func()
        else:
            ctx['ssh'] = deps.build_ssh_adapter_func(
                runtime_context.ssh_executor,
                execution_context.ssh_command_timeout_sec,
                deps.call_ssh_executor_func,
            )
    else:
        ctx['connection_method'] = 'none'

    try:
        res = deps.run_module_entrypoint_func(
            execution_context.mod,
            ctx,
            execution_context.code,
            execution_context.item_id,
        )
    except Exception as e:
        res = deps.build_exec_error_result_func(execution_context.code, execution_context.item_id, e)

    if execution_context.result_item_payload:
        res = {**execution_context.result_item_payload, **res}
    return res


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
    build_item_base_context_func=None,
    needs_host_connection_func=None,
    build_winrm_options_func=None,
    build_winrm_ssh_adapter_func=None,
    build_paramiko_ssh_blocker_func=None,
    build_ssh_adapter_func=None,
    call_ssh_executor_func=None,
    run_module_entrypoint_func=None,
    build_exec_error_result_func=None,
    deps=None,
    execution_context=None,
    runtime_context=None,
):
    if isinstance(mod, ItemExecutionContext) and isinstance(logger, ItemExecutionRuntime):
        execution_context = mod
        runtime_context = logger

    if deps is None:
        deps = ItemExecutionDispatchDeps(
            build_item_base_context_func=build_item_base_context_func,
            needs_host_connection_func=needs_host_connection_func,
            build_winrm_options_func=build_winrm_options_func,
            build_winrm_ssh_adapter_func=build_winrm_ssh_adapter_func,
            build_paramiko_ssh_blocker_func=build_paramiko_ssh_blocker_func,
            build_ssh_adapter_func=build_ssh_adapter_func,
            call_ssh_executor_func=call_ssh_executor_func,
            run_module_entrypoint_func=run_module_entrypoint_func,
            build_exec_error_result_func=build_exec_error_result_func,
        )
    if execution_context is None:
        execution_context = ItemExecutionContext(
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
        )
    if runtime_context is None:
        runtime_context = ItemExecutionRuntime(
            no_ssh_executor=no_ssh_executor,
            host=host,
            connection_values=connection_values,
            ssh_options=ssh_options,
            thresholds=thresholds,
            paramiko_client_factory=paramiko_client_factory,
            winrm_options=winrm_options,
            winrm_executor=winrm_executor,
            ssh_executor=ssh_executor,
        )
    return _execute_item_after_precheck_gate_with_context(execution_context, runtime_context, deps)


def _build_item_execution_deps(
    deps=None,
    gate_deps=None,
    dispatch_deps=None,
    evaluate_item_precheck_gate_func=None,
    build_missing_item_result_func=None,
    normalize_application_token_func=None,
    log_result_json_func=None,
    execute_item_after_precheck_gate_func=None,
    log_item_result_summary_func=None,
    sleep_func=None,
):
    if deps is not None:
        return deps
    return ItemExecutionDeps(
        evaluate_item_precheck_gate_func=evaluate_item_precheck_gate_func,
        build_missing_item_result_func=build_missing_item_result_func,
        normalize_application_token_func=normalize_application_token_func,
        log_result_json_func=log_result_json_func,
        execute_item_after_precheck_gate_func=execute_item_after_precheck_gate_func,
        log_item_result_summary_func=log_item_result_summary_func,
        sleep_func=sleep_func,
        gate_deps=gate_deps,
        dispatch_deps=dispatch_deps,
    )


def _build_item_execution_loop_context(
    items,
    available,
    logger,
    credentials,
    port,
    user,
    password,
    precheck_errors,
    become_precheck_errors,
    item_sleep_sec,
):
    if isinstance(items, ItemExecutionLoopContext):
        return items
    return ItemExecutionLoopContext(
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
    )


def _build_item_execution_loop_runtime(
    no_ssh_executor,
    host,
    ssh_options,
    thresholds,
    paramiko_client_factory,
    winrm_options,
    winrm_executor,
    ssh_executor,
):
    if isinstance(no_ssh_executor, ItemExecutionLoopRuntime):
        return no_ssh_executor
    return ItemExecutionLoopRuntime(
        no_ssh_executor=no_ssh_executor,
        host=host,
        ssh_options=ssh_options,
        thresholds=thresholds,
        paramiko_client_factory=paramiko_client_factory,
        winrm_options=winrm_options,
        winrm_executor=winrm_executor,
        ssh_executor=ssh_executor,
    )


def _runtime_for_gate(loop_runtime, connection_values):
    return ItemExecutionRuntime(
        no_ssh_executor=loop_runtime.no_ssh_executor,
        host=loop_runtime.host,
        connection_values=connection_values,
        ssh_options=loop_runtime.ssh_options,
        thresholds=loop_runtime.thresholds,
        paramiko_client_factory=loop_runtime.paramiko_client_factory,
        winrm_options=loop_runtime.winrm_options,
        winrm_executor=loop_runtime.winrm_executor,
        ssh_executor=loop_runtime.ssh_executor,
    )


def _run_item_execution_loop_with_context(loop_context, loop_runtime, deps):
    results = []
    items = loop_context.items
    for idx, it in enumerate(items):
        gate = _call_with_optional_deps(
            deps.evaluate_item_precheck_gate_func,
            (
                it,
                loop_context.available,
                loop_context.logger,
                loop_context.credentials,
                loop_context.port,
                loop_context.user,
                loop_context.password,
                loop_context.precheck_errors,
                loop_context.become_precheck_errors,
            ),
            deps.gate_deps,
        )
        code = gate['code']
        item_id = gate['item_id']
        item_payload = gate['item_payload']
        result_item_payload = gate['result_item_payload']
        mod = gate['mod']
        db_error = gate['db_error']
        method = gate['method']
        ssh_command_timeout_sec = gate['ssh_command_timeout_sec']
        connection_credential = gate['connection_credential']
        connection_values = gate['connection_values']
        app_credential = gate['app_credential']
        app_credential_data = gate['app_credential_data']
        if gate['should_skip']:
            res = gate['result']
            results.append(res)
            deps.log_result_json_func(loop_context.logger, res)
            continue
        if not mod:
            res = deps.build_missing_item_result_func(code, item_id, result_item_payload, db_error)
            results.append(res)
            loop_context.logger.warning(
                'item not found: inspection_code=%s request_application_type=%s request_application=%s request_application_family=%s db_error=%s',
                code,
                deps.normalize_application_token_func((item_payload or {}).get('application_type_name')),
                deps.normalize_application_token_func((item_payload or {}).get('application_name')),
                deps.normalize_application_token_func((item_payload or {}).get('application_family_name')),
                db_error or '',
            )
            deps.log_result_json_func(loop_context.logger, res)
            continue

        execution_context = ItemExecutionContext(
            mod=mod,
            logger=loop_context.logger,
            code=code,
            item_id=item_id,
            result_item_payload=result_item_payload,
            method=method,
            ssh_command_timeout_sec=ssh_command_timeout_sec,
            connection_credential=connection_credential,
            app_credential=app_credential,
            app_credential_data=app_credential_data,
        )
        runtime_context = _runtime_for_gate(loop_runtime, connection_values)
        res = _call_with_optional_deps(
            deps.execute_item_after_precheck_gate_func,
            (execution_context, runtime_context),
            deps.dispatch_deps,
        )
        results.append(res)
        deps.log_item_result_summary_func(loop_context.logger, code, res)
        if loop_context.item_sleep_sec > 0 and idx < (len(items) - 1):
            deps.sleep_func(loop_context.item_sleep_sec)
    return results


def run_item_execution_loop(
    items=None,
    available=None,
    logger=None,
    credentials=None,
    port=None,
    user=None,
    password=None,
    precheck_errors=None,
    become_precheck_errors=None,
    no_ssh_executor=None,
    host=None,
    ssh_options=None,
    thresholds=None,
    paramiko_client_factory=None,
    winrm_options=None,
    winrm_executor=None,
    ssh_executor=None,
    item_sleep_sec=None,
    deps=None,
    gate_deps=None,
    dispatch_deps=None,
    evaluate_item_precheck_gate_func=None,
    build_missing_item_result_func=None,
    normalize_application_token_func=None,
    log_result_json_func=None,
    execute_item_after_precheck_gate_func=None,
    log_item_result_summary_func=None,
    sleep_func=None,
    loop_context=None,
    loop_runtime=None,
):
    deps = _build_item_execution_deps(
        deps=deps,
        gate_deps=gate_deps,
        dispatch_deps=dispatch_deps,
        evaluate_item_precheck_gate_func=evaluate_item_precheck_gate_func,
        build_missing_item_result_func=build_missing_item_result_func,
        normalize_application_token_func=normalize_application_token_func,
        log_result_json_func=log_result_json_func,
        execute_item_after_precheck_gate_func=execute_item_after_precheck_gate_func,
        log_item_result_summary_func=log_item_result_summary_func,
        sleep_func=sleep_func,
    )
    if loop_context is None and isinstance(items, ItemExecutionLoopContext):
        loop_context = items
    if loop_runtime is None and isinstance(available, ItemExecutionLoopRuntime):
        loop_runtime = available
    if loop_context is None:
        loop_context = _build_item_execution_loop_context(
            items,
            available,
            logger,
            credentials,
            port,
            user,
            password,
            precheck_errors,
            become_precheck_errors,
            item_sleep_sec,
        )
    if loop_runtime is None:
        loop_runtime = _build_item_execution_loop_runtime(
            no_ssh_executor,
            host,
            ssh_options,
            thresholds,
            paramiko_client_factory,
            winrm_options,
            winrm_executor,
            ssh_executor,
        )
    return _run_item_execution_loop_with_context(loop_context, loop_runtime, deps)
