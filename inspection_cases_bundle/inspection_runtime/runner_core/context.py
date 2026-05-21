#!/usr/bin/env python3
# -*- coding: utf-8 -*-


def build_winrm_ssh_adapter(winrm_executor, wr_opts):
    def _winrm_ssh_adapter(_cmd, _host, _port, _user, _password, _ssh_options):
        return winrm_executor(
            _cmd,
            _host,
            _port,
            _user,
            _password,
            _ssh_options,
            wr_opts,
        )

    return _winrm_ssh_adapter


def build_ssh_adapter(ssh_executor, ssh_command_timeout_sec, call_ssh_executor_func):
    def _ssh_adapter(_cmd, _host, _port, _user, _password, _ssh_options):
        return call_ssh_executor_func(
            ssh_executor,
            _cmd,
            _host,
            _port,
            _user,
            _password,
            _ssh_options,
            ssh_command_timeout_sec,
        )

    return _ssh_adapter


def build_paramiko_ssh_blocker():
    def _paramiko_ssh_blocker(_cmd, _host, _port, _user, _password, _ssh_options):
        return (
            1,
            '',
            'paramiko connection method does not support _ssh; use _run_paramiko_commands',
        )

    return _paramiko_ssh_blocker


def build_item_base_context(
    no_ssh_executor,
    host,
    connection_values,
    ssh_options,
    thresholds,
    code,
    item_id,
    result_item_payload,
    ssh_command_timeout_sec,
    connection_credential,
    app_credential,
    app_credential_data,
    paramiko_client_factory,
):
    return {
        'ssh': no_ssh_executor,
        'host': host,
        'port': connection_values.get('port'),
        'user': connection_values.get('user'),
        'password': connection_values.get('password'),
        'os_user': connection_values.get('user'),
        'os_password': connection_values.get('password'),
        'ssh_options': ssh_options,
        'thresholds': thresholds.get(code, {}),
        'inspection_code': code,
        'item_id': item_id,
        'item_payload': result_item_payload or {},
        'ssh_command_timeout_sec': ssh_command_timeout_sec,
        'connection_credential': connection_credential or {},
        'connection_credential_data': connection_values.get('data') or {},
        'application_credential': app_credential or {},
        'application_credential_data': app_credential_data,
        'paramiko_client_factory': paramiko_client_factory,
    }

