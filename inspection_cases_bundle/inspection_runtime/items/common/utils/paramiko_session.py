# -*- coding: utf-8 -*-
"""Pure Paramiko session identity/cache helpers.

These helpers preserve the Stage 7-3A BaseCheck session reuse semantics.
They intentionally do not open, close, or cache sessions themselves except for
close_paramiko_session(), which mirrors the previous local close helper.
"""

import hashlib


def paramiko_secret_hash(value):
    if value in (None, ''):
        return ''
    return hashlib.sha1(str(value).encode('utf-8')).hexdigest()


def close_paramiko_session(session):
    if not isinstance(session, dict):
        return

    channel = session.get('channel')
    client = session.get('client')

    if channel is not None:
        try:
            channel.close()
        except Exception:
            pass

    if client is not None:
        try:
            client.close()
        except Exception:
            pass


def build_paramiko_profile_key(resolved_profile, normalize_algorithm_list_func):
    if isinstance(resolved_profile, dict):
        pager_patterns = tuple(str(x) for x in (resolved_profile.get('pager_patterns') or []))
        pager_response = str(resolved_profile.get('pager_response', ' '))
        extra_kex_algorithms = normalize_algorithm_list_func(
            resolved_profile.get('extra_kex_algorithms')
        )
        extra_host_key_algorithms = normalize_algorithm_list_func(
            resolved_profile.get('extra_host_key_algorithms')
        )
        return (
            pager_patterns,
            pager_response,
            extra_kex_algorithms,
            extra_host_key_algorithms,
        )
    return str(resolved_profile or '')


def build_paramiko_become_key(become_config):
    if not become_config:
        return (False, '', '', '')
    return (
        True,
        str(become_config.get('method') or ''),
        str(become_config.get('user') or ''),
        paramiko_secret_hash(become_config.get('password') or ''),
    )


def build_paramiko_session_key(
    ctx,
    options,
    resolved_profile,
    enable_required,
    profile_key_func,
    become_key_func,
    become_config=None,
):
    return (
        ctx.get('host'),
        int(ctx.get('port') or 22),
        ctx.get('user') or '',
        paramiko_secret_hash(ctx.get('password') or ''),
        str(options.get('auth_method') or 'auto'),
        str(options.get('key_filename') or ''),
        paramiko_secret_hash(options.get('private_key') or ''),
        paramiko_secret_hash(options.get('private_key_passphrase') or ''),
        bool(options.get('allow_agent', False)),
        bool(options.get('look_for_keys', False)),
        profile_key_func(resolved_profile),
        bool(enable_required),
        become_key_func(become_config),
    )


def is_paramiko_session_alive(session):
    if not isinstance(session, dict):
        return False

    client = session.get('client')
    channel = session.get('channel')
    if client is None or channel is None:
        return False

    try:
        if getattr(channel, 'closed', False):
            return False
    except Exception:
        return False

    try:
        transport = client.get_transport()
        if transport is None or not transport.is_active():
            return False
    except Exception:
        return False

    return True
