import os

from items.common.utils.encoding import decode_bytes
from items.common.utils.become import (
    normalize_become_method,
    parse_unix_id_uid as _parse_unix_id_uid,
)
from items.common.utils.paramiko_config import (
    paramiko_auth_attempts,
    load_paramiko_private_key as _load_paramiko_private_key,
)


def get_check_attr(mod, name, default=None):
    value = getattr(mod, name, None)
    if value is None and hasattr(mod, 'CHECK_CLASS'):
        value = getattr(mod.CHECK_CLASS, name, None)
    return default if value is None else value


def resolve_paramiko_options(mod):
    return {
        'profile': get_check_attr(mod, 'PARAMIKO_PROFILE', 'generic_network'),
        'auth_method': get_check_attr(mod, 'PARAMIKO_AUTH_METHOD', 'auto'),
        'key_filename': get_check_attr(mod, 'PARAMIKO_KEY_FILENAME', '~/.ssh/id_rsa.pub'),
        'private_key': get_check_attr(mod, 'PARAMIKO_PRIVATE_KEY', None),
        'private_key_passphrase': get_check_attr(mod, 'PARAMIKO_PRIVATE_KEY_PASSPHRASE', None),
        'allow_agent': get_check_attr(mod, 'PARAMIKO_ALLOW_AGENT', False),
        'look_for_keys': get_check_attr(mod, 'PARAMIKO_LOOK_FOR_KEYS', False),
        'timeout_sec': get_check_attr(mod, 'PARAMIKO_TIMEOUT_SEC', 10),
        'banner_timeout_sec': get_check_attr(mod, 'PARAMIKO_BANNER_TIMEOUT_SEC', 10),
        'auth_timeout_sec': get_check_attr(mod, 'PARAMIKO_AUTH_TIMEOUT_SEC', 10),
    }


def load_paramiko_private_key(private_key, passphrase, paramiko_module):
    return _load_paramiko_private_key(private_key, passphrase, paramiko_module)


def build_paramiko_connect_kwargs(host, port, user, password, options, auth_attempt, paramiko_module):
    kwargs = {
        'hostname': host,
        'port': int(port or 22),
        'username': user or None,
        'timeout': float(options.get('timeout_sec', 10)),
        'banner_timeout': float(options.get('banner_timeout_sec', 10)),
        'auth_timeout': float(options.get('auth_timeout_sec', 10)),
        'allow_agent': bool(options.get('allow_agent', False)),
        'look_for_keys': bool(options.get('look_for_keys', False)),
    }
    profile = (options or {}).get('profile')
    if profile:
        from items.common._base import BaseCheck

        profile_check = BaseCheck({})
        resolved_profile = profile_check._resolve_paramiko_profile(profile)
        transport_factory = profile_check._build_paramiko_transport_factory(resolved_profile, paramiko_module)
        if transport_factory is not None:
            kwargs['transport_factory'] = transport_factory

    if auth_attempt == 'password':
        kwargs['password'] = password or None
        kwargs['allow_agent'] = False
        kwargs['look_for_keys'] = False
        return kwargs

    passphrase = options.get('private_key_passphrase')
    private_key = options.get('private_key')
    if private_key:
        kwargs['pkey'] = load_paramiko_private_key(private_key, passphrase, paramiko_module)
    else:
        kwargs['key_filename'] = os.path.expanduser(str(options.get('key_filename') or '~/.ssh/id_rsa.pub'))
    if passphrase:
        kwargs['passphrase'] = passphrase
    return kwargs


def run_paramiko_precheck(host, port, user, password, options, client_factory=None):
    import paramiko

    auth_method = str((options or {}).get('auth_method') or 'auto').strip().lower()
    try:
        attempts = paramiko_auth_attempts(auth_method)
    except ValueError:
        return 255, '', f'PARAMIKO_CONNECTION_ERROR: unsupported auth_method: {auth_method}'

    last_error = None
    for attempt in attempts:
        client = client_factory() if client_factory else paramiko.SSHClient()
        try:
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(**build_paramiko_connect_kwargs(
                host,
                port,
                user,
                password,
                options or {},
                attempt,
                paramiko,
            ))
            channel = client.invoke_shell()
            try:
                channel.close()
            except Exception:
                pass
            client.close()
            return 0, '', ''
        except Exception as exc:
            last_error = exc
            try:
                client.close()
            except Exception:
                pass
            if auth_method != 'auto':
                break

    return 255, '', 'PARAMIKO_CONNECTION_ERROR: ' + str(last_error or 'authentication failed')


def run_paramiko_exec_command(host, port, user, password, options, command, client_factory=None):
    import paramiko

    auth_method = str((options or {}).get('auth_method') or 'auto').strip().lower()
    try:
        attempts = paramiko_auth_attempts(auth_method)
    except ValueError:
        return 255, '', f'PARAMIKO_CONNECTION_ERROR: unsupported auth_method: {auth_method}'

    last_error = None
    for attempt in attempts:
        client = client_factory() if client_factory else paramiko.SSHClient()
        try:
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(**build_paramiko_connect_kwargs(
                host,
                port,
                user,
                password,
                options or {},
                attempt,
                paramiko,
            ))
            timeout_sec = float((options or {}).get('timeout_sec', 10))
            _, stdout, stderr = client.exec_command(command, timeout=timeout_sec)
            out = decode_bytes(stdout.read() if stdout is not None else b'')
            err = decode_bytes(stderr.read() if stderr is not None else b'')
            channel = getattr(stdout, 'channel', None)
            if channel is not None and hasattr(channel, 'recv_exit_status'):
                rc = int(channel.recv_exit_status())
            else:
                rc = 0
            client.close()
            return rc, out, err
        except Exception as exc:
            last_error = exc
            try:
                client.close()
            except Exception:
                pass
            if auth_method != 'auto':
                break

    return 255, '', 'PARAMIKO_CONNECTION_ERROR: ' + str(last_error or 'authentication failed')


def parse_unix_id_uid(id_output):
    return _parse_unix_id_uid(id_output, missing_uid=None)


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
    from items.common._base import BaseCheck

    method = normalize_become_method(become_method)
    if method == 'su':
        su_command = 'su ' + (str(become_user or 'root').strip() or 'root')
    elif method == 'su -':
        su_command = 'su - ' + (str(become_user or 'root').strip() or 'root')
    else:
        return 255, '', f'PARAMIKO_BECOME_ERROR: unsupported become_method: {become_method}'

    class ParamikoBecomePrecheck(BaseCheck):
        USE_HOST_CONNECTION = True
        CONNECTION_METHOD = 'paramiko'
        PARAMIKO_PROFILE = 'linux'

    check = ParamikoBecomePrecheck({
        'host': host,
        'port': port,
        'user': user,
        'password': password,
        'inspection_code': 'PARAMIKO_BECOME_PRECHECK',
        'item_id': None,
        'paramiko_client_factory': client_factory,
    })
    check.PARAMIKO_AUTH_METHOD = (options or {}).get('auth_method', 'auto')
    check.PARAMIKO_PROFILE = (options or {}).get('profile', 'linux')
    check.PARAMIKO_KEY_FILENAME = (options or {}).get('key_filename', '~/.ssh/id_rsa.pub')
    check.PARAMIKO_PRIVATE_KEY = (options or {}).get('private_key')
    check.PARAMIKO_PRIVATE_KEY_PASSPHRASE = (options or {}).get('private_key_passphrase')
    check.PARAMIKO_ALLOW_AGENT = bool((options or {}).get('allow_agent', False))
    check.PARAMIKO_LOOK_FOR_KEYS = bool((options or {}).get('look_for_keys', False))
    check.PARAMIKO_TIMEOUT_SEC = float((options or {}).get('timeout_sec', 10))
    check.PARAMIKO_BANNER_TIMEOUT_SEC = float((options or {}).get('banner_timeout_sec', 10))
    check.PARAMIKO_AUTH_TIMEOUT_SEC = float((options or {}).get('auth_timeout_sec', 10))

    verify_command = 'id'
    results = check._run_paramiko_commands([
        {
            'command': su_command,
            'timeout': 1,
            'ignore_prompt': True,
        },
        {
            'command': str(become_password or ''),
            'hide_command': True,
        },
        verify_command,
    ])
    failed = [
        item for item in results
        if item.get('rc') != 0 and not (item.get('command') == su_command and item.get('timed_out'))
    ]
    if failed:
        first = failed[0]
        return int(first.get('rc') or 1), first.get('stdout') or '', first.get('stderr') or '권한 상승 실패'

    verify_result = next((item for item in reversed(results) if item.get('command') == verify_command), None)
    verify_output = (verify_result or {}).get('stdout') or ''
    expected_user = str(become_user or 'root').strip() or 'root'
    uid, user_name = parse_unix_id_uid(verify_output)
    if expected_user == 'root' and uid == '0':
        return 0, verify_output, ''
    if expected_user != 'root' and user_name == expected_user:
        return 0, verify_output, ''
    return 1, verify_output, (
        f'권한 상승 사용자 확인 실패: expected_user={expected_user}, '
        f'actual_user={user_name}, actual_uid={uid or ""}, output={verify_output.strip()}'
    )
