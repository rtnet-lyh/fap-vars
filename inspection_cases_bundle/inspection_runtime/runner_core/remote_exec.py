# -*- coding: utf-8 -*-
"""Remote and shell execution helpers for inspection runner.

This module contains SSH, WinRM, no-ssh, shell item, and module-runner
fallback execution helpers extracted from ``runner.py``. Keep return tuple
and result dictionary behavior compatible with the runner public wrappers.
"""

import json
from functools import lru_cache

from items.common.utils.command_result import (
    select_shell_failure_raw_output,
    strip_shell_output_text,
)
from runner_core.context import (
    build_winrm_ssh_adapter as _build_winrm_ssh_adapter,
    build_ssh_adapter as _build_ssh_adapter,
)
from runner_core.item_execution import call_module_run as _call_module_run
from runner_core.remote import (
    create_winrm_session as _create_winrm_session,
    run_winrm_with_session as _run_winrm_with_session,
    run_ssh_with_helpers as _run_ssh_with_helpers,
    run_no_ssh as _run_no_ssh,
)
from runner_core.results import build_no_runner_result as _build_no_runner_result


def run_ssh(
    cmd,
    host,
    port,
    user,
    password,
    ssh_options,
    timeout_sec=None,
    normalize_timeout_func=None,
    strip_runtime_warnings_func=None,
    default_timeout_sec=None,
    timeout_rc=None,
):
    return _run_ssh_with_helpers(
        cmd,
        host,
        port,
        user,
        password,
        ssh_options,
        timeout_sec=timeout_sec,
        normalize_timeout_func=normalize_timeout_func,
        strip_runtime_warnings_func=strip_runtime_warnings_func,
        default_timeout_sec=default_timeout_sec,
        timeout_rc=timeout_rc,
    )


@lru_cache(maxsize=64)
def _winrm_session(host, port, user, password, transport, server_cert_validation, operation_timeout_sec, read_timeout_sec):
    return _create_winrm_session(
        host,
        port,
        user,
        password,
        transport,
        server_cert_validation,
        operation_timeout_sec,
        read_timeout_sec,
    )


def run_winrm(
    cmd,
    host,
    port,
    user,
    password,
    _ssh_options,
    winrm_options=None,
    decode_stream_bytes_func=None,
    strip_runtime_warnings_func=None,
    session_factory=None,
):
    if session_factory is None:
        session_factory = _winrm_session
    return _run_winrm_with_session(
        cmd,
        host,
        port,
        user,
        password,
        _ssh_options,
        winrm_options,
        session_factory=session_factory,
        decode_stream_bytes_func=decode_stream_bytes_func,
        strip_runtime_warnings_func=strip_runtime_warnings_func,
    )


def run_no_ssh(cmd, host, port, user, password, ssh_options):
    return _run_no_ssh(cmd, host, port, user, password, ssh_options)


def build_winrm_ssh_adapter(winrm_executor, wr_opts):
    return _build_winrm_ssh_adapter(winrm_executor, wr_opts)


def build_ssh_adapter(ssh_executor, ssh_command_timeout_sec, call_ssh_executor_func):
    return _build_ssh_adapter(ssh_executor, ssh_command_timeout_sec, call_ssh_executor_func)


def run_shell_item(mod, ctx):
    # shell 항목은 원격에서 실행하고 JSON 결과만 받는 것을 기본 규칙으로 한다.
    script_path = getattr(mod, 'SCRIPT_PATH', None)
    inline = getattr(mod, 'SCRIPT_INLINE', None)
    inspection_code = ctx.get('inspection_code')
    item_id = ctx.get('item_id')
    if not script_path and not inline:
        data = {
            'inspection_code': inspection_code,
            'status': 'fail',
            'error': '쉘 스크립트 미정의',
            'raw_output': 'SCRIPT_PATH/SCRIPT_INLINE 값이 모두 비어 있음',
        }
        if item_id is not None:
            data['item_id'] = item_id
        return data

    if script_path:
        cmd = f"bash {script_path}"
    else:
        # inline script execution
        cmd = "bash -lc " + json.dumps(inline)

    rc, out, err = ctx['ssh'](cmd, ctx['host'], ctx['port'], ctx['user'], ctx['password'], ctx['ssh_options'])
    if rc != 0:
        raw = select_shell_failure_raw_output(out, err)
        data = {
            'inspection_code': inspection_code,
            'status': 'fail',
            'error': '원격 명령 실행 실패',
            'stderr': strip_shell_output_text(err),
            'raw_output': raw,
        }
        if item_id is not None:
            data['item_id'] = item_id
        return data

    # shell 출력은 JSON 형태만 허용한다.
    try:
        data = json.loads(strip_shell_output_text(out))
    except Exception:
        data = {
            'inspection_code': inspection_code,
            'status': 'fail',
            'error': 'JSON 파싱 실패',
            'stdout': strip_shell_output_text(out),
            'raw_output': strip_shell_output_text(out),
        }
        if item_id is not None:
            data['item_id'] = item_id
        return data

    if 'inspection_code' not in data:
        data['inspection_code'] = inspection_code
    if item_id is not None:
        data['item_id'] = item_id
    return data


def call_module_run(mod, ctx):
    return _call_module_run(mod, ctx)


def build_no_runner_result(code, item_id):
    return _build_no_runner_result(code, item_id)
