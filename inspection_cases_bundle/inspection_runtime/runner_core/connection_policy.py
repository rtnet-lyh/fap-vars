# -*- coding: utf-8 -*-

from items.common.utils.credentials import (
    normalize_credential_key as _normalize_credential_key,
    credential_data_or_empty,
    preferred_credential_value,
    flatten_credentials as _flatten_credentials,
    filter_credentials as _filter_credentials_impl,
    pick_credential as _pick_credential_impl,
    select_application_credential as _select_application_credential_impl,
)


def needs_host_connection(mod):
    val = getattr(mod, 'USE_HOST_CONNECTION', None)
    if val is not None:
        return bool(val)
    if hasattr(mod, 'CHECK_CLASS'):
        return bool(getattr(mod.CHECK_CLASS, 'USE_HOST_CONNECTION', True))
    return True


def get_connection_method(mod, item_payload):
    """항목별 원격 연결 방식을 결정한다.

    우선순위:
    1) 항목 모듈의 CONNECTION_METHOD
    2) CHECK_CLASS.CONNECTION_METHOD
    3) item payload의 connection_method
    4) inspection_code prefix(W-*, PC-*)는 winrm
    5) 기본 ssh
    """
    val = getattr(mod, 'CONNECTION_METHOD', None)
    if val is None and hasattr(mod, 'CHECK_CLASS'):
        val = getattr(mod.CHECK_CLASS, 'CONNECTION_METHOD', None)
    if val is None:
        val = (item_payload or {}).get('connection_method')
    if isinstance(val, str) and val.strip():
        return val.strip().lower()

    code = (item_payload or {}).get('inspection_code') or ''
    if isinstance(code, str) and (code.upper().startswith('W-') or code.upper().startswith('PC-')):
        return 'winrm'
    return 'ssh'


def normalize_credential_key(value):
    return _normalize_credential_key(value)


def flatten_credentials(credentials_map):
    return _flatten_credentials(credentials_map)


def is_network_item(inspection_code):
    code = str(inspection_code or '').strip().upper()
    for prefix in (
        'N-', 'S-', 'M-', 'CA-',
        'OP-NW-', 'OF-NW-', 'RD-NW-',
        'OP-SD-', 'OF-SD-', 'RD-SD-',
    ):
        if code.startswith(prefix):
            return True
    return False


def _filter_credentials(entries, credential_types=None, application_types=None):
    return _filter_credentials_impl(entries, credential_types, application_types)


def _pick_credential(entries, application_id=None, application_type_id=None):
    return _pick_credential_impl(
        entries,
        application_id=application_id,
        application_type_id=application_type_id,
    )


def select_connection_credential(credentials_map, method, item_payload):
    item_payload = item_payload or {}
    entries = flatten_credentials(credentials_map)
    application_id = item_payload.get('application_id')
    application_type_id = item_payload.get('application_type_id')
    inspection_code = item_payload.get('inspection_code')

    if method == 'winrm':
        strategies = [
            (['WINRM'], ['WINDOWS']),
            (['WINRM'], None),
        ]
    elif method == 'paramiko':
        strategies = [
            (['SSH'], ['LINUX']),
            (['SSH'], ['UNIX']),
            (['NETWORK_DEVICE'], ['LINUX']),
            (['NETWORK_DEVICE'], ['UNIX']),
            (['NETWORK_DEVICE'], ['NETWORK']),
            (['SSH'], ['NETWORK']),
            (['NETWORK_DEVICE'], None),
            (['SSH'], None),
        ]
    elif is_network_item(inspection_code):
        strategies = [
            (['NETWORK_DEVICE'], ['NETWORK']),
            (['SSH'], ['NETWORK']),
            (['NETWORK_DEVICE'], None),
            (['SSH'], None),
        ]
    else:
        strategies = [
            (['SSH'], ['UNIX', 'LINUX']),
            (['SSH'], ['LINUX']),
            (['SSH'], ['UNIX']),
            (['SSH'], None),
        ]

    for credential_types, application_types in strategies:
        selected = _pick_credential(
            _filter_credentials(entries, credential_types, application_types),
            application_id=application_id,
            application_type_id=application_type_id,
        )
        if selected:
            return selected

    return None


def select_application_credential(credentials_map, item_payload):
    return _select_application_credential_impl(credentials_map, item_payload)


def resolve_connection_values(base_port, method, credential, fallback_user, fallback_password):
    data = {}
    if isinstance(credential, dict):
        data = credential.get('data') or {}
        if not isinstance(data, dict):
            data = {}

    user = data.get('username')
    if user in (None, ''):
        user = fallback_user

    password = data.get('password')
    if password in (None, ''):
        password = fallback_password

    resolved_port = base_port
    for key in ('port', 'ssh_port', 'winrm_port'):
        value = data.get(key)
        if value not in (None, ''):
            try:
                resolved_port = int(str(value).strip())
            except Exception:
                pass
            break

    if resolved_port in (None, '', 0):
        resolved_port = 22

    try:
        resolved_port = int(resolved_port)
    except Exception:
        resolved_port = 22

    if method == 'winrm' and resolved_port == 22:
        resolved_port = 5985

    return {
        'user': user or '',
        'password': password or '',
        'port': resolved_port,
        'data': data,
    }


def get_credential_data(credential):
    return credential_data_or_empty(credential)


def get_preferred_credential_value(application_credential, connection_credential, key, default=None):
    return preferred_credential_value(
        get_credential_data(application_credential),
        get_credential_data(connection_credential),
        key,
        default,
    )
