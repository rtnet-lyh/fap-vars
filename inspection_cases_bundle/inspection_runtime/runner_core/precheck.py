# -*- coding: utf-8 -*-

import shlex
from dataclasses import dataclass

from items.common.utils.become import normalize_become_method
from items.common.utils.credentials import credential_data_or_empty, preferred_credential_value
from items.common.utils.options import is_truthy_value


@dataclass(frozen=True)
class HostPrecheckLoopContext:
    items: object
    available: object
    logger: object
    credentials: object
    host: object
    port: object
    user: object
    password: object
    ssh_options: object
    winrm_options: object
    common_token: object


@dataclass(frozen=True)
class HostPrecheckLoopRuntime:
    winrm_executor: object
    ssh_executor: object
    paramiko_client_factory: object


@dataclass(frozen=True)
class HostPrecheckLoopDeps:
    normalize_item_func: object
    build_lookup_payload_func: object
    resolve_runtime_item_module_func: object
    needs_host_connection_func: object
    get_connection_method_func: object
    select_connection_credential_func: object
    resolve_connection_values_func: object
    run_host_precheck_for_method_func: object
    format_precheck_error_func: object


@dataclass(frozen=True)
class BecomePrecheckLoopContext:
    items: object
    available: object
    logger: object
    credentials: object
    host: object
    port: object
    user: object
    password: object
    ssh_options: object
    precheck_errors: object
    common_token: object


@dataclass(frozen=True)
class BecomePrecheckLoopRuntime:
    ssh_executor: object
    paramiko_client_factory: object


@dataclass(frozen=True)
class BecomePrecheckLoopDeps:
    normalize_item_func: object
    build_lookup_payload_func: object
    resolve_runtime_item_module_func: object
    needs_host_connection_func: object
    get_connection_method_func: object
    select_connection_credential_func: object
    resolve_connection_values_func: object
    select_application_credential_func: object
    build_become_precheck_request_func: object
    run_become_precheck_for_request_func: object
    format_precheck_error_func: object


def build_become_precheck_command(become_method, become_user, become_password):
    password_arg = shlex.quote(str(become_password or ''))
    if become_method == 'sudo':
        return "printf '%s\\n' {password} | sudo -S -p '' -v".format(password=password_arg)
    if become_method in ('su', 'su -'):
        user_arg = shlex.quote(str(become_user or 'root').strip() or 'root')
        return "printf '%s\\n' {password} | su - {user} -c true".format(
            password=password_arg,
            user=user_arg,
        )
    return None


def build_become_precheck_request(
    method,
    item_payload,
    connection_values,
    connection_credential,
    application_credential,
):
    method = str(method or '').strip().lower()
    if method not in ('ssh', 'paramiko'):
        return None

    become = preferred_credential_value(
        credential_data_or_empty(application_credential),
        credential_data_or_empty(connection_credential),
        'become',
        False,
    )
    if not is_truthy_value(become):
        return None

    become_method = normalize_become_method(
        preferred_credential_value(
            credential_data_or_empty(application_credential),
            credential_data_or_empty(connection_credential),
            'become_method',
            '',
        )
    )
    if become_method not in ('sudo', 'su', 'su -'):
        return None

    become_user_value = preferred_credential_value(
        credential_data_or_empty(application_credential),
        credential_data_or_empty(connection_credential),
        'become_user',
        'root',
    )
    become_password_value = preferred_credential_value(
        credential_data_or_empty(application_credential),
        credential_data_or_empty(connection_credential),
        'become_password',
        '',
    )
    become_user = str(become_user_value or 'root').strip() or 'root'
    become_password = str(become_password_value or '')
    command = build_become_precheck_command(become_method, become_user, become_password)
    if not command:
        return None

    key = (
        method,
        str((connection_values or {}).get('port') or ''),
        str((connection_values or {}).get('user') or ''),
        become_method,
        become_user,
        become_password,
    )
    return {
        'key': key,
        'method': method,
        'become_method': become_method,
        'become_user': become_user,
        'become_password': become_password,
        'command': command,
    }

def format_precheck_error(err, out, fallback):
    return (err or out or '').strip() or fallback



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
    build_winrm_options_func,
    run_paramiko_precheck_func,
    resolve_paramiko_options_func,
    call_ssh_executor_func,
    default_ssh_command_timeout_sec,
):
    if method == 'winrm':
        wr_opts = build_winrm_options_func(mod, winrm_options)
        return winrm_executor(
            'Write-Output FAP_CONNECTION_OK',
            host,
            connection_values.get('port'),
            connection_values.get('user'),
            connection_values.get('password'),
            ssh_options,
            wr_opts,
        )
    if method == 'paramiko':
        return run_paramiko_precheck_func(
            host,
            connection_values.get('port'),
            connection_values.get('user'),
            connection_values.get('password'),
            resolve_paramiko_options_func(mod),
            client_factory=paramiko_client_factory,
        )
    return call_ssh_executor_func(
        ssh_executor,
        'true',
        host,
        connection_values.get('port'),
        connection_values.get('user'),
        connection_values.get('password'),
        ssh_options,
        default_ssh_command_timeout_sec,
    )


def _run_host_precheck_loop_with_context(context, runtime, deps):
    precheck_errors = {}
    checked_methods = set()
    for it in context.items:
        code, _, item_payload = deps.normalize_item_func(it)
        lookup_payload = deps.build_lookup_payload_func(code, item_payload)
        mod, module_key, module_source, db_error = deps.resolve_runtime_item_module_func(
            context.available,
            lookup_payload,
            context.logger,
        )
        if not mod or not deps.needs_host_connection_func(mod):
            continue
        method = deps.get_connection_method_func(mod, lookup_payload)
        if method in checked_methods or method in precheck_errors:
            continue
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
        rc, out, err = deps.run_host_precheck_for_method_func(
            method,
            mod,
            context.host,
            connection_values,
            context.ssh_options,
            context.winrm_options,
            runtime.winrm_executor,
            runtime.ssh_executor,
            runtime.paramiko_client_factory,
        )
        if rc != 0:
            precheck_errors[method] = deps.format_precheck_error_func(err, out, '연결 실패')
            context.logger.error(
                'host precheck failed: method=%s inspection_code=%s application_type=%s application=%s message=%s',
                method,
                module_key[0] if module_key else code,
                module_key[1] if module_key else context.common_token,
                module_key[2] if module_key else context.common_token,
                precheck_errors[method],
            )
            continue
        checked_methods.add(method)
        context.logger.info(
            'host precheck ok: method=%s source=%s inspection_code=%s application_type=%s application=%s',
            method,
            module_source,
            module_key[0] if module_key else code,
            module_key[1] if module_key else context.common_token,
            module_key[2] if module_key else context.common_token,
        )
    return precheck_errors, checked_methods


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
    normalize_item_func,
    build_lookup_payload_func,
    resolve_runtime_item_module_func,
    needs_host_connection_func,
    get_connection_method_func,
    select_connection_credential_func,
    resolve_connection_values_func,
    run_host_precheck_for_method_func,
    format_precheck_error_func,
    common_token,
):
    context = HostPrecheckLoopContext(
        items=items,
        available=available,
        logger=logger,
        credentials=credentials,
        host=host,
        port=port,
        user=user,
        password=password,
        ssh_options=ssh_options,
        winrm_options=winrm_options,
        common_token=common_token,
    )
    runtime = HostPrecheckLoopRuntime(
        winrm_executor=winrm_executor,
        ssh_executor=ssh_executor,
        paramiko_client_factory=paramiko_client_factory,
    )
    deps = HostPrecheckLoopDeps(
        normalize_item_func=normalize_item_func,
        build_lookup_payload_func=build_lookup_payload_func,
        resolve_runtime_item_module_func=resolve_runtime_item_module_func,
        needs_host_connection_func=needs_host_connection_func,
        get_connection_method_func=get_connection_method_func,
        select_connection_credential_func=select_connection_credential_func,
        resolve_connection_values_func=resolve_connection_values_func,
        run_host_precheck_for_method_func=run_host_precheck_for_method_func,
        format_precheck_error_func=format_precheck_error_func,
    )
    return _run_host_precheck_loop_with_context(context, runtime, deps)


def _run_become_precheck_loop_with_context(context, runtime, deps):
    become_precheck_errors = {}
    checked_become_prechecks = set()
    for it in context.items:
        code, _, item_payload = deps.normalize_item_func(it)
        lookup_payload = deps.build_lookup_payload_func(code, item_payload)
        mod, module_key, module_source, db_error = deps.resolve_runtime_item_module_func(
            context.available,
            lookup_payload,
            context.logger,
        )
        if not mod or not deps.needs_host_connection_func(mod):
            continue
        method = deps.get_connection_method_func(mod, lookup_payload)
        if method in context.precheck_errors:
            continue
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
        app_credential = deps.select_application_credential_func(context.credentials, lookup_payload)
        become_request = deps.build_become_precheck_request_func(
            method,
            lookup_payload,
            connection_values,
            connection_credential,
            app_credential,
        )
        if not become_request:
            continue
        become_key = become_request['key']
        if become_key in checked_become_prechecks or become_key in become_precheck_errors:
            continue
        rc, out, err = deps.run_become_precheck_for_request_func(
            method,
            mod,
            context.host,
            connection_values,
            context.ssh_options,
            runtime.ssh_executor,
            runtime.paramiko_client_factory,
            become_request,
        )
        if rc != 0:
            become_precheck_errors[become_key] = deps.format_precheck_error_func(err, out, '권한 상승 실패')
            context.logger.error(
                'become precheck failed: method=%s become_method=%s inspection_code=%s application_type=%s application=%s message=%s',
                method,
                become_request.get('become_method') or '',
                module_key[0] if module_key else code,
                module_key[1] if module_key else context.common_token,
                module_key[2] if module_key else context.common_token,
                become_precheck_errors[become_key],
            )
            continue
        checked_become_prechecks.add(become_key)
        context.logger.info(
            'become precheck ok: method=%s become_method=%s source=%s inspection_code=%s application_type=%s application=%s',
            method,
            become_request.get('become_method') or '',
            module_source,
            module_key[0] if module_key else code,
            module_key[1] if module_key else context.common_token,
            module_key[2] if module_key else context.common_token,
        )
    return become_precheck_errors, checked_become_prechecks


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
    normalize_item_func,
    build_lookup_payload_func,
    resolve_runtime_item_module_func,
    needs_host_connection_func,
    get_connection_method_func,
    select_connection_credential_func,
    resolve_connection_values_func,
    select_application_credential_func,
    build_become_precheck_request_func,
    run_become_precheck_for_request_func,
    format_precheck_error_func,
    common_token,
):
    context = BecomePrecheckLoopContext(
        items=items,
        available=available,
        logger=logger,
        credentials=credentials,
        host=host,
        port=port,
        user=user,
        password=password,
        ssh_options=ssh_options,
        precheck_errors=precheck_errors,
        common_token=common_token,
    )
    runtime = BecomePrecheckLoopRuntime(
        ssh_executor=ssh_executor,
        paramiko_client_factory=paramiko_client_factory,
    )
    deps = BecomePrecheckLoopDeps(
        normalize_item_func=normalize_item_func,
        build_lookup_payload_func=build_lookup_payload_func,
        resolve_runtime_item_module_func=resolve_runtime_item_module_func,
        needs_host_connection_func=needs_host_connection_func,
        get_connection_method_func=get_connection_method_func,
        select_connection_credential_func=select_connection_credential_func,
        resolve_connection_values_func=resolve_connection_values_func,
        select_application_credential_func=select_application_credential_func,
        build_become_precheck_request_func=build_become_precheck_request_func,
        run_become_precheck_for_request_func=run_become_precheck_for_request_func,
        format_precheck_error_func=format_precheck_error_func,
    )
    return _run_become_precheck_loop_with_context(context, runtime, deps)


def run_become_precheck_for_request(
    method,
    mod,
    host,
    connection_values,
    ssh_options,
    ssh_executor,
    paramiko_client_factory,
    become_request,
    run_paramiko_su_precheck_func,
    run_paramiko_exec_command_func,
    resolve_paramiko_options_func,
    call_ssh_executor_func,
    default_ssh_command_timeout_sec,
):
    if method == 'paramiko' and become_request.get('become_method') in ('su', 'su -'):
        return run_paramiko_su_precheck_func(
            host,
            connection_values.get('port'),
            connection_values.get('user'),
            connection_values.get('password'),
            resolve_paramiko_options_func(mod),
            become_request.get('become_method'),
            become_request.get('become_user'),
            become_request.get('become_password'),
            client_factory=paramiko_client_factory,
        )
    if method == 'paramiko':
        return run_paramiko_exec_command_func(
            host,
            connection_values.get('port'),
            connection_values.get('user'),
            connection_values.get('password'),
            resolve_paramiko_options_func(mod),
            become_request['command'],
            client_factory=paramiko_client_factory,
        )
    return call_ssh_executor_func(
        ssh_executor,
        become_request['command'],
        host,
        connection_values.get('port'),
        connection_values.get('user'),
        connection_values.get('password'),
        ssh_options,
        default_ssh_command_timeout_sec,
    )

