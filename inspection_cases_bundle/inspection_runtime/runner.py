#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import codecs
import io
import json
import os
import subprocess
import sys
import importlib
import inspect
import types
import hashlib
import logging
import datetime
import time
import re
import traceback
import shlex
from functools import lru_cache

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ITEMS_DIR = os.path.join(BASE_DIR, 'items')
# items 패키지를 import할 수 있도록 BASE_DIR를 sys.path에 추가한다.
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

COMMON_TOKEN = 'A'
APPLICATION_NAME_ALIASES = {
    '': COMMON_TOKEN,
    '보안장비': 'SECURITY',
    '집중기간 모니터링': 'PEAK_MONITORING',
    '사전준비': 'PRECHECK',
    '제어시스템': 'CONTROL_SYSTEM',
    '이동통신': 'MOBILE',
    '백업': 'BACKUP',
    '클라우드': 'CLOUD',
    '스토리지': 'STORAGE',
    '기타': 'ETC',
    '시큐아이': 'SECUI',
    '컨테이너': 'CONTAINER',
    '전원': 'POWER',
    '방화벽': 'FIREWALL',
}

RUNTIME_WARNING_PATTERNS = (
    re.compile(r'^(?:/bin/sh|bash): warning: setlocale: LC_ALL: cannot change locale \([^)]+\)\s*$'),
    re.compile(r'^setlocale: LC_ALL: cannot change locale \([^)]+\)\s*$'),
    re.compile(r'^bash: cannot set terminal process group \([^)]+\): Inappropriate ioctl for device\s*$'),
    re.compile(r'^bash: no job control in this shell\s*$'),
    re.compile(r'^(?:stdin: is not a tty|mesg: ttyname failed: Inappropriate ioctl for device)\s*$'),
    re.compile(r'^tput: No value for \$TERM and no -T specified\s*$'),
)

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
POWERSHELL_UTF8_PREFIX = (
    "$OutputEncoding = [System.Text.UTF8Encoding]::new($false); "
    "[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); "
)
SUPPORTED_BECOME_PRECHECK_METHODS = ('sudo', 'su', 'su -')
TRUTHY_VALUES = ('1', 'true', 'y', 'yes', 'on')
SSH_CONTROL_MASTER_OPTION_NAMES = ('controlmaster', 'controlpersist', 'controlpath')


def decode_stream_bytes(value, preferred_encodings=None):
    if value is None:
        return value
    if not isinstance(value, bytes):
        return str(value)
    if not value:
        return ''

    candidates = []
    if value.startswith(codecs.BOM_UTF8):
        candidates.append('utf-8-sig')
    candidates.append('utf-8')

    if value.startswith(codecs.BOM_UTF16_LE):
        candidates.append('utf-16-le')
    elif value.startswith(codecs.BOM_UTF16_BE):
        candidates.append('utf-16-be')
    elif b'\x00' in value:
        candidates.extend(['utf-16-le', 'utf-16-be'])

    for encoding in preferred_encodings or ():
        if encoding:
            candidates.append(str(encoding).strip())

    candidates.extend(['cp949', 'euc-kr', 'cp1252'])

    seen = set()
    for encoding in candidates:
        if not encoding or encoding in seen:
            continue
        seen.add(encoding)
        try:
            return value.decode(encoding)
        except (LookupError, UnicodeDecodeError):
            continue

    return value.decode('utf-8', 'replace')


def coerce_text(value):
    if value is None:
        return value
    if isinstance(value, bytes):
        return decode_stream_bytes(value)
    return str(value)


def strip_runtime_warnings(text):
    text = coerce_text(text)
    if not text:
        return text

    cleaned_lines = []
    for line in str(text).splitlines():
        stripped = line.strip()
        if any(pattern.match(stripped) for pattern in RUNTIME_WARNING_PATTERNS):
            continue
        cleaned_lines.append(line)

    result = '\n'.join(cleaned_lines)
    if text.endswith('\n') and result:
        result += '\n'
    return result


def normalize_ssh_command_timeout_sec(value, default=DEFAULT_SSH_COMMAND_TIMEOUT_SEC):
    try:
        resolved = int(str(value).strip())
    except Exception:
        resolved = int(default)
    if resolved <= 0:
        resolved = int(default)
    return resolved


def resolve_ssh_command_timeout_sec(mod, default=DEFAULT_SSH_COMMAND_TIMEOUT_SEC):
    timeout_value = getattr(mod, 'SSH_COMMAND_TIMEOUT_SEC', None)
    if timeout_value is None and hasattr(mod, 'CHECK_CLASS'):
        timeout_value = getattr(mod.CHECK_CLASS, 'SSH_COMMAND_TIMEOUT_SEC', None)
    return normalize_ssh_command_timeout_sec(timeout_value, default)


def executor_accepts_timeout_arg(executor):
    try:
        params = inspect.signature(executor).parameters.values()
    except (TypeError, ValueError):
        return True

    positional_count = 0
    for param in params:
        if param.kind == inspect.Parameter.VAR_POSITIONAL:
            return True
        if param.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD):
            positional_count += 1
    return positional_count >= 7


def call_ssh_executor(executor, cmd, host, port, user, password, ssh_options, timeout_sec):
    if executor_accepts_timeout_arg(executor):
        return executor(cmd, host, port, user, password, ssh_options, timeout_sec)
    return executor(cmd, host, port, user, password, ssh_options)


def load_item_module(module_name):
    return importlib.import_module(module_name)


def sanitize_identifier(value):
    text = str(value or '').strip()
    text = re.sub(r'[^A-Za-z0-9_]+', '_', text)
    text = re.sub(r'_+', '_', text).strip('_')
    return text or 'unknown'


@lru_cache(maxsize=512)
def load_db_item_module(module_name, script_text):
    module = types.ModuleType(module_name)
    module.__file__ = f'<{module_name}>'
    module.__package__ = 'items'
    module.__dict__['__builtins__'] = __builtins__
    sys.modules[module_name] = module
    exec(compile(script_text, module.__file__, 'exec'), module.__dict__)
    return module


def get_inline_script_text(item_payload):
    payload = item_payload or {}
    for key in ('inspection_script', 'check_script'):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def format_exception_only_text(exc):
    try:
        return ''.join(traceback.format_exception_only(type(exc), exc)).strip()
    except Exception:
        return str(exc)


def normalize_application_token(value):
    text = str(value or '').strip()
    if text in APPLICATION_NAME_ALIASES:
        return APPLICATION_NAME_ALIASES[text]
    text = text.upper()
    text = re.sub(r'[^A-Z0-9]+', '_', text)
    text = re.sub(r'_+', '_', text).strip('_')
    return text or COMMON_TOKEN


def infer_item_descriptor(module_name):
    # module_name 예:
    # - items.U-06__UNIX__A__A -> ('U-06', 'UNIX', 'A', 'A')
    # - items.U-06__UNIX__A -> ('U-06', 'UNIX', 'A', 'A')
    # - items.U-06_file_owner -> ('U-06', 'A', 'A', 'A')
    base = module_name.split('.')[-1]
    if '__' in base:
        parts = base.split('__')
        if len(parts) == 4:
            return (
                parts[0],
                normalize_application_token(parts[1]),
                normalize_application_token(parts[2]),
                normalize_application_token(parts[3]),
            )
        if len(parts) == 3:
            return (
                parts[0],
                normalize_application_token(parts[1]),
                normalize_application_token(parts[2]),
                COMMON_TOKEN,
            )
    return base.split('_')[0], COMMON_TOKEN, COMMON_TOKEN, COMMON_TOKEN


def get_module_lookup_key(mod, module_name):
    item_code, item_app_type, item_app, item_app_version = infer_item_descriptor(module_name)
    return build_module_lookup_key(
        mod,
        item_code,
        item_app_type,
        item_app,
        item_app_version,
    )


def build_module_lookup_key(mod, item_code, item_app_type, item_app, item_app_version):
    explicit_code = getattr(mod, 'ITEM_ID', None)
    if not explicit_code and hasattr(mod, 'CHECK_CLASS'):
        explicit_code = getattr(mod.CHECK_CLASS, 'ITEM_ID', None)
    if explicit_code:
        item_code = explicit_code

    explicit_app_type = getattr(mod, 'APPLICATION_TYPE', None)
    if explicit_app_type is None and hasattr(mod, 'CHECK_CLASS'):
        explicit_app_type = getattr(mod.CHECK_CLASS, 'APPLICATION_TYPE', None)
    if explicit_app_type is not None:
        item_app_type = normalize_application_token(explicit_app_type)

    explicit_app = getattr(mod, 'APPLICATION', None)
    if explicit_app is None and hasattr(mod, 'CHECK_CLASS'):
        explicit_app = getattr(mod.CHECK_CLASS, 'APPLICATION', None)
    if explicit_app is not None:
        item_app = normalize_application_token(explicit_app)

    explicit_app_version = getattr(mod, 'APPLICATION_VERSION', None)
    if explicit_app_version is None and hasattr(mod, 'CHECK_CLASS'):
        explicit_app_version = getattr(mod.CHECK_CLASS, 'APPLICATION_VERSION', None)
    if explicit_app_version is not None:
        item_app_version = normalize_application_token(explicit_app_version)

    return item_code, item_app_type, item_app, item_app_version


def build_db_module_name(item_payload, script_text):
    payload = item_payload or {}
    code = sanitize_identifier(payload.get('inspection_code'))
    app_key = sanitize_identifier(
        payload.get('host_application_id')
        or payload.get('application_id')
        or payload.get('item_id')
    )
    script_hash = hashlib.sha1(script_text.encode('utf-8')).hexdigest()[:12]
    return f'items._db_{code}_{app_key}_{script_hash}'


def iter_module_candidates(item_payload):
    payload = item_payload or {}
    code = payload.get('inspection_code')
    app_type = normalize_application_token(payload.get('application_type_name'))
    app = normalize_application_token(payload.get('application_name'))
    app_family = normalize_application_token(payload.get('application_family_name'))

    candidates = [
        (code, app_type, app, app_family),
        (code, app_type, app, COMMON_TOKEN),
        (code, app_type, COMMON_TOKEN, COMMON_TOKEN),
        (code, COMMON_TOKEN, app, COMMON_TOKEN),
        (code, COMMON_TOKEN, COMMON_TOKEN, COMMON_TOKEN),
    ]
    seen = set()
    for key in candidates:
        if not key[0] or key in seen:
            continue
        seen.add(key)
        yield key


def resolve_item_module(available, item_payload):
    for key in iter_module_candidates(item_payload):
        mod = available.get(key)
        if mod:
            return mod, key
    return None, None


def resolve_runtime_item_module(available, item_payload, logger=None):
    payload = item_payload or {}
    script_text = get_inline_script_text(payload)
    db_error = None

    if script_text:
        try:
            module_name = build_db_module_name(payload, script_text)
            mod = load_db_item_module(module_name, script_text)
            module_key = build_module_lookup_key(
                mod,
                payload.get('inspection_code'),
                normalize_application_token(payload.get('application_type_name')),
                normalize_application_token(payload.get('application_name')),
                normalize_application_token(payload.get('application_family_name')),
            )
            return mod, module_key, 'db', None
        except Exception as exc:
            db_error = format_exception_only_text(exc)
            if logger:
                logger.warning(
                    'db item load failed. fallback to file: inspection_code=%s application_type=%s application=%s family=%s error=%s',
                    payload.get('inspection_code'),
                    payload.get('application_type_name'),
                    payload.get('application_name'),
                    payload.get('application_family_name'),
                    db_error,
                )

    mod, module_key = resolve_item_module(available, payload)
    if mod:
        return mod, module_key, 'file', db_error

    return None, None, None, db_error


def sanitize_item_payload(item_payload):
    if not item_payload:
        return {}
    sanitized = dict(item_payload)
    sanitized.pop('inspection_script', None)
    sanitized.pop('check_script', None)
    return sanitized


def normalize_credential_key(value):
    if value is None:
        return ''
    return str(value).strip().upper()


def flatten_credentials(credentials_map):
    entries = []
    for bucket_key, values in (credentials_map or {}).items():
        if not isinstance(values, list):
            continue
        for entry in values:
            if not isinstance(entry, dict):
                continue
            copied = dict(entry)
            if not copied.get('application_type_name'):
                copied['application_type_name'] = bucket_key
            copied['_credential_bucket_key'] = bucket_key
            entries.append(copied)
    return entries


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
    filtered = []
    normalized_credential_types = {normalize_credential_key(x) for x in (credential_types or [])}
    normalized_application_types = {normalize_credential_key(x) for x in (application_types or [])}

    for entry in entries:
        credential_type_name = normalize_credential_key(entry.get('credential_type_name'))
        application_type_name = normalize_credential_key(
            entry.get('application_type_name') or entry.get('_credential_bucket_key')
        )
        if normalized_credential_types and credential_type_name not in normalized_credential_types:
            continue
        if normalized_application_types and application_type_name not in normalized_application_types:
            continue
        filtered.append(entry)

    return filtered


def _pick_credential(entries, application_id=None, application_type_id=None):
    if not entries:
        return None

    if application_id is not None:
        for entry in entries:
            if str(entry.get('application_id')) == str(application_id):
                return entry

    if application_type_id is not None:
        for entry in entries:
            if str(entry.get('application_type_id')) == str(application_type_id):
                return entry

    return entries[0]


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
    item_payload = item_payload or {}
    credentials_map = credentials_map or {}

    application_type_name = normalize_credential_key(item_payload.get('application_type_name'))
    application_type_id = item_payload.get('application_type_id')
    application_id = item_payload.get('application_id')

    candidates = []
    if application_type_name:
        candidates = credentials_map.get(application_type_name) or []

    def pick(entries):
        if not isinstance(entries, list) or not entries:
            return None
        if application_id is not None:
            for entry in entries:
                if str(entry.get('application_id')) == str(application_id):
                    return entry
        if application_type_id is not None:
            for entry in entries:
                if str(entry.get('application_type_id')) == str(application_type_id):
                    return entry
        return entries[0]

    selected = pick(candidates)
    if selected:
        return selected

    for key, entries in credentials_map.items():
        if application_type_name and normalize_credential_key(key) != application_type_name:
            continue
        selected = pick(entries)
        if selected:
            return selected

    if application_type_id is None and application_id is None:
        return None

    for entries in credentials_map.values():
        selected = pick(entries)
        if selected:
            return selected

    return None


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


def is_truthy(value):
    if isinstance(value, bool):
        return value
    return str(value or '').strip().lower() in TRUTHY_VALUES


def normalize_bool_option(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in ('1', 'true', 'yes', 'y', 'on'):
        return True
    if text in ('0', 'false', 'no', 'n', 'off'):
        return False
    return default


def normalize_become_method(value):
    return ' '.join(str(value or '').strip().lower().split())


def get_credential_data(credential):
    if not isinstance(credential, dict):
        return {}
    data = credential.get('data') or {}
    if isinstance(data, dict):
        return data
    return {}


def get_preferred_credential_value(application_credential, connection_credential, key, default=None):
    for data in (
        get_credential_data(application_credential),
        get_credential_data(connection_credential),
    ):
        if key not in data:
            continue
        value = data.get(key)
        if value not in (None, ''):
            return value
    return default


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

    become = get_preferred_credential_value(application_credential, connection_credential, 'become', False)
    if not is_truthy(become):
        return None

    become_method = normalize_become_method(
        get_preferred_credential_value(application_credential, connection_credential, 'become_method', '')
    )
    if become_method not in SUPPORTED_BECOME_PRECHECK_METHODS:
        return None

    become_user_value = get_preferred_credential_value(
        application_credential,
        connection_credential,
        'become_user',
        'root',
    )
    become_password_value = get_preferred_credential_value(
        application_credential,
        connection_credential,
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


def run_ssh(cmd, host, port, user, password, ssh_options, timeout_sec=None):
    import shutil
    resolved_timeout_sec = normalize_ssh_command_timeout_sec(timeout_sec, DEFAULT_SSH_COMMAND_TIMEOUT_SEC)
    # SSH 실행 기본 커맨드 구성
    base_cmd = ['ssh', '-p', str(port)]
    if ssh_options:
        base_cmd += ssh_options.split()
    target = f"{user}@{host}" if user else host
    base_cmd.append(target)
    base_cmd.append(cmd)
    if password:
        # 패스워드 인증이면 sshpass 사용 (없으면 실패 처리)
        sshpass = shutil.which('sshpass')
        if not sshpass:
            return (1, '', 'sshpass not installed for password auth')
        base_cmd = [sshpass, '-p', password] + base_cmd
    try:
        proc = subprocess.run(
            base_cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=resolved_timeout_sec,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = strip_runtime_warnings(exc.stdout) or ''
        stderr = strip_runtime_warnings(exc.stderr) or ''
        timeout_message = f'SSH_COMMAND_TIMEOUT: exceeded {resolved_timeout_sec}s'
        if stderr:
            stderr = f'{stderr.rstrip()}\n{timeout_message}'
        else:
            stderr = timeout_message
        return SSH_COMMAND_TIMEOUT_RC, stdout, stderr
    stdout = strip_runtime_warnings(proc.stdout)
    stderr = strip_runtime_warnings(proc.stderr)
    return proc.returncode, stdout, stderr


def get_check_attr(mod, name, default=None):
    value = getattr(mod, name, None)
    if value is None and hasattr(mod, 'CHECK_CLASS'):
        value = getattr(mod.CHECK_CLASS, name, None)
    return default if value is None else value


def get_explicit_check_class_attr(mod, name):
    check_class = getattr(mod, 'CHECK_CLASS', None)
    if check_class is None:
        return None
    for cls in getattr(check_class, '__mro__', (check_class,)):
        if getattr(cls, '__name__', '') == 'BaseCheck':
            break
        class_dict = getattr(cls, '__dict__', {})
        if name in class_dict:
            return class_dict.get(name)
    return None


def get_payload_host_vars(item_payload):
    host_vars = (item_payload or {}).get('host_vars') or {}
    return host_vars if isinstance(host_vars, dict) else {}


def get_host_check_attr(mod, item_payload, name, default=None):
    host_vars = get_payload_host_vars(item_payload)
    if name in host_vars:
        value = host_vars.get(name)
        if value not in (None, ''):
            return value
    return get_check_attr(mod, name, default)


def normalize_connection_method_value(value, allow_unknown=False):
    text = str(value or '').strip()
    if not text:
        return None
    normalized = re.sub(r'[^A-Za-z0-9]+', '_', text).strip('_').upper()
    if normalized == 'SSH':
        return 'ssh'
    if normalized == 'WINRM':
        return 'winrm'
    if normalized == 'PARAMIKO':
        return 'paramiko'
    if normalized == 'NETWORK_DEVICE':
        return 'paramiko'
    if allow_unknown:
        return text.lower()
    return None


def get_payload_connection_method(item_payload):
    payload = item_payload or {}
    method = normalize_connection_method_value(payload.get('connection_method'), allow_unknown=True)
    if method:
        return method
    for key in ('execution_account_type', 'credential_type_name', 'credential_type'):
        method = normalize_connection_method_value(payload.get(key))
        if method:
            return method
    return None


def resolve_paramiko_options(mod, item_payload=None):
    from items.common._base import BaseCheck

    return {
        'auth_method': get_host_check_attr(mod, item_payload, 'PARAMIKO_AUTH_METHOD', BaseCheck.PARAMIKO_AUTH_METHOD),
        'key_filename': get_host_check_attr(mod, item_payload, 'PARAMIKO_KEY_FILENAME', BaseCheck.PARAMIKO_KEY_FILENAME),
        'private_key': get_host_check_attr(mod, item_payload, 'PARAMIKO_PRIVATE_KEY', BaseCheck.PARAMIKO_PRIVATE_KEY),
        'private_key_passphrase': get_host_check_attr(
            mod,
            item_payload,
            'PARAMIKO_PRIVATE_KEY_PASSPHRASE',
            BaseCheck.PARAMIKO_PRIVATE_KEY_PASSPHRASE,
        ),
        'allow_agent': normalize_bool_option(
            get_host_check_attr(mod, item_payload, 'PARAMIKO_ALLOW_AGENT', BaseCheck.PARAMIKO_ALLOW_AGENT),
            BaseCheck.PARAMIKO_ALLOW_AGENT,
        ),
        'look_for_keys': normalize_bool_option(
            get_host_check_attr(mod, item_payload, 'PARAMIKO_LOOK_FOR_KEYS', BaseCheck.PARAMIKO_LOOK_FOR_KEYS),
            BaseCheck.PARAMIKO_LOOK_FOR_KEYS,
        ),
        'timeout_sec': get_host_check_attr(mod, item_payload, 'PARAMIKO_TIMEOUT_SEC', BaseCheck.PARAMIKO_TIMEOUT_SEC),
        'banner_timeout_sec': get_host_check_attr(
            mod,
            item_payload,
            'PARAMIKO_BANNER_TIMEOUT_SEC',
            BaseCheck.PARAMIKO_BANNER_TIMEOUT_SEC,
        ),
        'auth_timeout_sec': get_host_check_attr(
            mod,
            item_payload,
            'PARAMIKO_AUTH_TIMEOUT_SEC',
            BaseCheck.PARAMIKO_AUTH_TIMEOUT_SEC,
        ),
    }


def load_paramiko_private_key(private_key, passphrase, paramiko_module):
    key_stream = io.StringIO(str(private_key))
    key_classes = [
        paramiko_module.RSAKey,
        paramiko_module.ECDSAKey,
        paramiko_module.Ed25519Key,
    ]
    dss_key = getattr(paramiko_module, 'DSSKey', None)
    if dss_key:
        key_classes.append(dss_key)

    last_error = None
    for key_cls in key_classes:
        key_stream.seek(0)
        try:
            return key_cls.from_private_key(key_stream, password=passphrase or None)
        except Exception as exc:
            last_error = exc
    if last_error:
        raise last_error
    raise ValueError('unsupported private key')


def build_paramiko_connect_kwargs(host, port, user, password, options, auth_attempt, paramiko_module):
    kwargs = {
        'hostname': host,
        'port': int(port or 22),
        'username': user or None,
        'timeout': float(options.get('timeout_sec', 10)),
        'banner_timeout': float(options.get('banner_timeout_sec', 10)),
        'auth_timeout': float(options.get('auth_timeout_sec', 10)),
        'allow_agent': normalize_bool_option(options.get('allow_agent'), False),
        'look_for_keys': normalize_bool_option(options.get('look_for_keys'), False),
    }
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
    if auth_method not in ('auto', 'key', 'password'):
        return 255, '', f'PARAMIKO_CONNECTION_ERROR: unsupported auth_method: {auth_method}'

    attempts = []
    if auth_method in ('auto', 'key'):
        attempts.append('key')
    if auth_method in ('auto', 'password'):
        attempts.append('password')

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
    if auth_method not in ('auto', 'key', 'password'):
        return 255, '', f'PARAMIKO_CONNECTION_ERROR: unsupported auth_method: {auth_method}'

    attempts = []
    if auth_method in ('auto', 'key'):
        attempts.append('key')
    if auth_method in ('auto', 'password'):
        attempts.append('password')

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
            out = decode_stream_bytes(stdout.read() if stdout is not None else b'')
            err = decode_stream_bytes(stderr.read() if stderr is not None else b'')
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
    match = re.search(r'(?:^|\s)uid=(\d+)(?:\(([^)]*)\))?', str(id_output or ''))
    if not match:
        return None, ''
    return match.group(1), match.group(2) or ''


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
            'ignore_prompt': True           
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


def ensure_ssh_options_defaults(ssh_options):
    text = (ssh_options or '').strip()
    required = [
        '-o ConnectTimeout=3',
        '-o ConnectionAttempts=1',
    ]
    for opt in required:
        if opt not in text:
            text = f'{text} {opt}'.strip()
    return text


def is_falsey(value):
    if isinstance(value, str):
        return value.strip().lower() in ('0', 'false', 'n', 'no', 'off')
    return value is False


def get_ssh_option_name(option):
    return str(option or '').split('=', 1)[0].strip().lower()


def strip_ssh_control_master_options(ssh_options):
    tokens = str(ssh_options or '').split()
    filtered = []
    idx = 0

    while idx < len(tokens):
        token = tokens[idx]
        if token == '-o' and idx + 1 < len(tokens):
            option = tokens[idx + 1]
            if get_ssh_option_name(option) in SSH_CONTROL_MASTER_OPTION_NAMES:
                idx += 2
                continue
            filtered.extend((token, option))
            idx += 2
            continue
        if token.startswith('-o') and get_ssh_option_name(token[2:]) in SSH_CONTROL_MASTER_OPTION_NAMES:
            idx += 1
            continue
        filtered.append(token)
        idx += 1

    return ' '.join(filtered)


def resolve_item_ssh_options(mod, ssh_options):
    item_ssh_options = ensure_ssh_options_defaults(ssh_options)
    if is_falsey(get_check_attr(mod, 'SSH_CONTROL_MASTER', None)):
        item_ssh_options = strip_ssh_control_master_options(item_ssh_options)
    return item_ssh_options


def get_item_host_vars(item_payload):
    if not isinstance(item_payload, dict):
        return {}
    host_vars = item_payload.get('host_vars') or {}
    return host_vars if isinstance(host_vars, dict) else {}


def resolve_winrm_shell(mod):
    shell = getattr(mod, 'WINRM_SHELL', None)
    if shell is None and hasattr(mod, 'CHECK_CLASS'):
        shell = getattr(mod.CHECK_CLASS, 'WINRM_SHELL', None)
    return shell


def resolve_item_winrm_options(winrm_options, item_payload, shell=None):
    opts = dict(winrm_options or {})
    winrm_transport = get_item_host_vars(item_payload).get('winrm_transport')
    if winrm_transport not in (None, ''):
        opts['transport'] = str(winrm_transport).strip().lower()
    if shell:
        opts['shell'] = shell
    return opts

def build_winrm_precheck_key(winrm_options):
    opts = winrm_options or {}
    return (
        str(opts.get('transport', 'ntlm')).strip().lower(),
        str(opts.get('server_cert_validation', 'ignore')),
        str(opts.get('operation_timeout_sec', 30)),
        str(opts.get('read_timeout_sec', 60)),
        str(opts.get('shell') or 'powershell').strip().lower(),
    )

def build_host_precheck_key(method, ssh_options, winrm_options=None):
    if method == 'ssh':
        return method, str(ssh_options or '')
    if method == 'winrm':
        return method, build_winrm_precheck_key(winrm_options)
    return method

def build_become_precheck_key(become_request, method, ssh_options):
    key = become_request['key']
    if method == 'ssh':
        return key, str(ssh_options or '')
    return key


@lru_cache(maxsize=64)
def _winrm_session(host, port, user, password, transport, server_cert_validation, operation_timeout_sec, read_timeout_sec):
    import winrm
    endpoint = f"http://{host}:{port}/wsman"
    if int(port) == 5986:
        endpoint = f"https://{host}:{port}/wsman"
    return winrm.Session(
        target=endpoint,
        auth=(user or '', password or ''),
        transport=transport,
        server_cert_validation=server_cert_validation,
        operation_timeout_sec=operation_timeout_sec,
        read_timeout_sec=read_timeout_sec,
    )


def run_winrm(cmd, host, port, user, password, _ssh_options, winrm_options=None):
    """WinRM 기반 원격 명령 실행.

    반환 형식은 SSH 실행과 동일하게 (rc, stdout, stderr)로 맞춘다.
    """
    opts = winrm_options or {}
    transport = opts.get('transport', 'ntlm')
    server_cert_validation = opts.get('server_cert_validation', 'ignore')
    operation_timeout_sec = int(opts.get('operation_timeout_sec', 30))
    read_timeout_sec = int(opts.get('read_timeout_sec', 60))
    shell = (opts.get('shell') or 'powershell').lower()

    try:
        session = _winrm_session(
            host,
            int(port),
            user or '',
            password or '',
            transport,
            server_cert_validation,
            operation_timeout_sec,
            read_timeout_sec,
        )
    except Exception as exc:
        return 901, '', 'WINRM_UNAVAILABLE: ' + str(exc)

    try:
        if shell == 'cmd':
            resp = session.run_cmd(cmd)
        else:
            resp = session.run_ps(POWERSHELL_UTF8_PREFIX + cmd)
        out = strip_runtime_warnings(decode_stream_bytes(resp.std_out or b''))
        err = strip_runtime_warnings(decode_stream_bytes(resp.std_err or b''))
        return int(resp.status_code), out, err
    except Exception as exc:
        return 902, '', 'WINRM_EXEC_ERROR: ' + str(exc)


def run_no_ssh(cmd, host, port, user, password, ssh_options):
    # SSH 사용 불가(로컬 항목에서 오동작 방지)
    return (1, '', 'ssh is not allowed for this item')


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
    2) CHECK_CLASS에 직접 정의한 CONNECTION_METHOD
    3) item payload의 실행 계정 형식(connection_method/credential_type_name 등)
    4) 기본 paramiko
    """
    val = getattr(mod, 'CONNECTION_METHOD', None)
    if val is None:
        val = get_explicit_check_class_attr(mod, 'CONNECTION_METHOD')
    if val is None:
        val = get_payload_connection_method(item_payload)
    if isinstance(val, str) and val.strip():
        return val.strip().lower()
    return 'paramiko'


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
        raw = out.strip() if out and out.strip() else err.strip()
        data = {
            'inspection_code': inspection_code,
            'status': 'fail',
            'error': '원격 명령 실행 실패',
            'stderr': err.strip(),
            'raw_output': raw,
        }
        if item_id is not None:
            data['item_id'] = item_id
        return data

    # shell 출력은 JSON 형태만 허용한다.
    try:
        data = json.loads(out.strip())
    except Exception:
        data = {
            'inspection_code': inspection_code,
            'status': 'fail',
            'error': 'JSON 파싱 실패',
            'stdout': out.strip(),
            'raw_output': out.strip(),
        }
        if item_id is not None:
            data['item_id'] = item_id
        return data

    if 'inspection_code' not in data:
        data['inspection_code'] = inspection_code
    if item_id is not None:
        data['item_id'] = item_id
    return data


def init_logger(job_id, execution_id, host, host_id):
    date_dir = datetime.datetime.now().strftime('%Y%m%d')
    base_dir = '/fap/logs/ansible'
    log_dir = os.path.join(base_dir, date_dir)
    os.makedirs(log_dir, exist_ok=True)
    safe_host = (host or 'nohost').replace(':', '_').replace('/', '_')
    safe_job = str(job_id) if job_id is not None else 'nojob'
    safe_exec = str(execution_id) if execution_id is not None else 'noexec'
    log_path = os.path.join(
        log_dir,
        f'job-{safe_job}_exec-{safe_exec}_host-{safe_host}.log',
    )

    logger = logging.getLogger('inspection_runner')
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(log_path, encoding='utf-8')
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


def summarize_result(res):
    # 로그에 넣기 좋은 요약 (원문 전체 로그 방지)
    status = res.get('status')
    error = res.get('error')
    message = res.get('message') or ''
    reasons = res.get('reasons')
    metrics = res.get('metrics')
    raw_output = res.get('raw_output')
    raw_len = len(raw_output) if isinstance(raw_output, str) else 0
    raw_preview = ''
    if isinstance(raw_output, str) and raw_output:
        raw_preview = raw_output.replace('\n', '\\n')[:200]
    return {
        'status': status,
        'error': error,
        'message': message,
        'reasons': reasons,
        'metrics': metrics,
        'raw_len': raw_len,
        'raw_preview': raw_preview,
    }


def build_precheck_fail_result(code, item_id, item_payload, method, err_text):
    message = f'{method.upper()} 연결 실패: {(err_text or "").strip()}'.strip()
    res = {
        'inspection_code': code,
        'item_id': item_id,
        'status': 'fail',
        'error': '호스트 연결 실패',
        'message': message,
        'raw_output': (err_text or '').strip(),
    }
    if item_payload:
        res = {**sanitize_item_payload(item_payload), **res}
    return res


def build_become_precheck_fail_result(code, item_id, item_payload, method, err_text):
    message = f'{method.upper()} 권한상승 사전 점검 실패: {(err_text or "").strip()}'.strip()
    res = {
        'inspection_code': code,
        'item_id': item_id,
        'status': 'fail',
        'error': '권한 상승 실패',
        'message': message,
        'raw_output': (err_text or '').strip(),
    }
    if item_payload:
        res = {**sanitize_item_payload(item_payload), **res}
    return res


def normalize_item(it):
    if isinstance(it, dict):
        return it.get('inspection_code'), it.get('item_id'), it
    return it, None, {}


def build_lookup_payload(code, item_payload):
    lookup_payload = {'inspection_code': code}
    if item_payload:
        lookup_payload.update(item_payload)
    return lookup_payload


def load_available_items(logger):
    available = {}
    available_codes = set()
    if not os.path.isdir(ITEMS_DIR):
        return available, available_codes

    # items 하위 폴더까지 재귀 탐색해 항목 모듈을 로드한다.
    for root, _, files in os.walk(ITEMS_DIR, followlinks=True):
        for fn in files:
            if not fn.endswith('.py') or fn.startswith('_'):
                continue
            if fn == '__init__.py':
                continue
            path = os.path.join(root, fn)
            rel = os.path.relpath(path, BASE_DIR)
            module_name = os.path.splitext(rel)[0].replace(os.sep, '.')
            # 예:
            # - items/U-06__UNIX__A__A.py -> module_name = items.U-06__UNIX__A__A
            # - items/U-06_file_owner.py -> module_name = items.U-06_file_owner
            mod = load_item_module(module_name)
            item_key = get_module_lookup_key(mod, module_name)
            if item_key in available:
                logger.warning(
                    'duplicate item key detected. latest module wins: inspection_code=%s application_type=%s application=%s module=%s',
                    item_key[0], item_key[1], item_key[2], module_name
                )
            available[item_key] = mod
            available_codes.add(item_key[0])

    return available, available_codes


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
        for it in items:
            code, _, item_payload = normalize_item(it)
            lookup_payload = build_lookup_payload(code, item_payload)
            mod, module_key, module_source, db_error = resolve_runtime_item_module(available, lookup_payload, logger)
            if not mod or not needs_host_connection(mod):
                continue
            method = get_connection_method(mod, lookup_payload)
            item_ssh_options = resolve_item_ssh_options(mod, ssh_options)
            item_winrm_options = None
            if method == 'winrm':
                item_winrm_options = resolve_item_winrm_options(
                    winrm_options,
                    lookup_payload,
                    resolve_winrm_shell(mod),
                )
            precheck_key = build_host_precheck_key(method, item_ssh_options, item_winrm_options)
            if precheck_key in checked_methods or precheck_key in precheck_errors:
                continue
            connection_credential = select_connection_credential(credentials, method, lookup_payload)
            connection_values = resolve_connection_values(port, method, connection_credential, user, password)
            
            if method == 'winrm':                
                rc, out, err = winrm_executor(
                    'Write-Output FAP_CONNECTION_OK',
                    host,
                    connection_values.get('port'),
                    connection_values.get('user'),
                    connection_values.get('password'),
                    ssh_options,
                    item_winrm_options,
                )
            elif method == 'paramiko':
                rc, out, err = run_paramiko_precheck(
                    host,
                    connection_values.get('port'),
                    connection_values.get('user'),
                    connection_values.get('password'),
                    resolve_paramiko_options(mod, lookup_payload),
                    client_factory=paramiko_client_factory,
                )
            else:
                rc, out, err = call_ssh_executor(
                    ssh_executor,
                    'true',
                    host,
                    connection_values.get('port'),
                    connection_values.get('user'),
                    connection_values.get('password'),
                    item_ssh_options,
                    DEFAULT_SSH_COMMAND_TIMEOUT_SEC,
                )
            # rc:16 --> cisco 장비 연결됨에도 불구하고 미지원 커맨드('true')로 에러나는 케이스
            if rc not in [0, 16]:
                precheck_errors[precheck_key] = (err or out or '').strip() or '연결 실패'
                logger.error(
                    'host precheck failed: method=%s inspection_code=%s application_type=%s application=%s message=%s',
                    method,
                    module_key[0] if module_key else code,
                    module_key[1] if module_key else COMMON_TOKEN,
                    module_key[2] if module_key else COMMON_TOKEN,
                    precheck_errors[precheck_key],
                )
                continue
            checked_methods.add(precheck_key)
            logger.info(
                'host precheck ok: method=%s source=%s inspection_code=%s application_type=%s application=%s',
                method,
                module_source,
                module_key[0] if module_key else code,
                module_key[1] if module_key else COMMON_TOKEN,
                module_key[2] if module_key else COMMON_TOKEN,
            )
        for it in items:
            code, _, item_payload = normalize_item(it)
            lookup_payload = build_lookup_payload(code, item_payload)
            mod, module_key, module_source, db_error = resolve_runtime_item_module(available, lookup_payload, logger)
            if not mod or not needs_host_connection(mod):
                continue
            method = get_connection_method(mod, lookup_payload)
            item_ssh_options = resolve_item_ssh_options(mod, ssh_options)
            item_winrm_options = None
            if mod and method == 'winrm':
                item_winrm_options = resolve_item_winrm_options(
                    winrm_options,
                    lookup_payload,
                    resolve_winrm_shell(mod),
                )
            precheck_key = build_host_precheck_key(method, item_ssh_options)
            if precheck_key in precheck_errors:
                continue
            connection_credential = select_connection_credential(credentials, method, lookup_payload)
            connection_values = resolve_connection_values(port, method, connection_credential, user, password)

            app_credential = select_application_credential(credentials, lookup_payload)
            become_request = build_become_precheck_request(
                method,
                lookup_payload,
                connection_values,
                connection_credential,
                app_credential,
            )

            if not become_request:
                continue
            become_key = build_become_precheck_key(become_request, method, item_ssh_options)
            if become_key in checked_become_prechecks or become_key in become_precheck_errors:
                continue
            if method == 'paramiko' and become_request.get('become_method') in ('su', 'su -'):
                rc, out, err = run_paramiko_su_precheck(
                    host,
                    connection_values.get('port'),
                    connection_values.get('user'),
                    connection_values.get('password'),
                    resolve_paramiko_options(mod, lookup_payload),
                    become_request.get('become_method'),
                    become_request.get('become_user'),
                    become_request.get('become_password'),
                    client_factory=paramiko_client_factory,
                )
            elif method == 'paramiko':
                rc, out, err = run_paramiko_exec_command(
                    host,
                    connection_values.get('port'),
                    connection_values.get('user'),
                    connection_values.get('password'),
                    resolve_paramiko_options(mod, lookup_payload),
                    become_request['command'],
                    client_factory=paramiko_client_factory,
                )
            else:
                rc, out, err = call_ssh_executor(
                    ssh_executor,
                    become_request['command'],
                    host,
                    connection_values.get('port'),
                    connection_values.get('user'),
                    connection_values.get('password'),
                    item_ssh_options,
                    DEFAULT_SSH_COMMAND_TIMEOUT_SEC,
                )
            if rc != 0:
                become_precheck_errors[become_key] = (err or out or '').strip() or '권한 상승 실패'
                logger.error(
                    'become precheck failed: method=%s become_method=%s inspection_code=%s application_type=%s application=%s message=%s',
                    method,
                    become_request.get('become_method') or '',
                    module_key[0] if module_key else code,
                    module_key[1] if module_key else COMMON_TOKEN,
                    module_key[2] if module_key else COMMON_TOKEN,
                    become_precheck_errors[become_key],
                )
                continue
            checked_become_prechecks.add(become_key)
            logger.info(
                'become precheck ok: method=%s become_method=%s source=%s inspection_code=%s application_type=%s application=%s',
                method,
                become_request.get('become_method') or '',
                module_source,
                module_key[0] if module_key else code,
                module_key[1] if module_key else COMMON_TOKEN,
                module_key[2] if module_key else COMMON_TOKEN,
            )
    else:
        logger.info('host precheck skipped.')

    results = []
    for idx, it in enumerate(items):
        code, item_id, item_payload = normalize_item(it)
        result_item_payload = sanitize_item_payload(item_payload)
        lookup_payload = build_lookup_payload(code, item_payload)
        mod, module_key, module_source, db_error = resolve_runtime_item_module(available, lookup_payload, logger)
        method = 'none'
        if mod and needs_host_connection(mod):
            method = get_connection_method(mod, lookup_payload)
        ssh_command_timeout_sec = None
        if mod and method == 'ssh':
            ssh_command_timeout_sec = resolve_ssh_command_timeout_sec(mod)
        item_ssh_options = resolve_item_ssh_options(mod, ssh_options)
        precheck_key = build_host_precheck_key(method, item_ssh_options)
        connection_credential = select_connection_credential(credentials, method, lookup_payload)
        connection_values = resolve_connection_values(port, method, connection_credential, user, password)
        app_credential = select_application_credential(credentials, lookup_payload)
        app_credential_data = {}
        if isinstance(app_credential, dict):
            app_credential_data = app_credential.get('data') or {}
        logger.info(
            '--- item start: inspection_code=%s item_id=%s source=%s method=%s conn_credential=%s req_app_type=%s req_app=%s req_app_version=%s matched_app_type=%s matched_app=%s matched_app_version=%s app_id=%s app_credential=%s',
            code,
            item_id,
            module_source or 'none',
            method,
            'yes' if connection_credential else 'no',
            (item_payload or {}).get('application_type_name'),
            (item_payload or {}).get('application_name'),
            (item_payload or {}).get('application_family_name'),
            module_key[1] if module_key else COMMON_TOKEN,
            module_key[2] if module_key else COMMON_TOKEN,
            module_key[3] if module_key else COMMON_TOKEN,
            (item_payload or {}).get('application_id'),
            'yes' if app_credential else 'no',
        )
        if precheck_key in precheck_errors:
            res = build_precheck_fail_result(code, item_id, item_payload, method, precheck_errors[precheck_key])
            results.append(res)
            logger.info('    result_json=\n%s', json.dumps(res, ensure_ascii=False, indent=2))
            continue
        become_request = None
        if mod:
            become_request = build_become_precheck_request(
                method,
                lookup_payload,
                connection_values,
                connection_credential,
                app_credential,
            )
        if become_request:
            become_key = build_become_precheck_key(become_request, method, item_ssh_options)
        if become_request and become_key in become_precheck_errors:
            res = build_become_precheck_fail_result(
                code,
                item_id,
                item_payload,
                method,
                become_precheck_errors[become_key],
            )
            results.append(res)
            logger.info('    result_json=\n%s', json.dumps(res, ensure_ascii=False, indent=2))
            continue
        if not mod:
            # 요청한 항목이 없으면 실패로 기록
            if db_error:
                res = {
                    'inspection_code': code,
                    'item_id': item_id,
                    'status': 'fail',
                    'error': 'script_load_error',
                    'message': db_error,
                    'raw_output': db_error,
                }
            else:
                res = {
                    'inspection_code': code,
                    'item_id': item_id,
                    'status': 'fail',
                    'error': '점검 스크립트 없음',
                    'message': '점검 스크립트 없음',
                    'raw_output': '점검 스크립트 없음',
                }
            if result_item_payload:
                res = {**result_item_payload, **res}
            results.append(res)
            logger.warning(
                'item not found: inspection_code=%s request_application_type=%s request_application=%s request_application_family=%s db_error=%s',
                code,
                normalize_application_token((item_payload or {}).get('application_type_name')),
                normalize_application_token((item_payload or {}).get('application_name')),
                normalize_application_token((item_payload or {}).get('application_family_name')),
                db_error or '',
            )
            logger.info('    result_json=\n%s', json.dumps(res, ensure_ascii=False, indent=2))
            continue

        ctx = {
            'ssh': no_ssh_executor,
            'host': host,
            'port': connection_values.get('port'),
            'user': connection_values.get('user'),
            'password': connection_values.get('password'),
            'os_user': connection_values.get('user'),
            'os_password': connection_values.get('password'),
            'ssh_options': item_ssh_options,
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
        logger.info("created ctx:\n%s", json.dumps(ctx, ensure_ascii=False, indent=2, default=str))
        if needs_host_connection(mod):
            ctx['connection_method'] = method
            if method == 'winrm':                
                ctx['ssh'] = lambda _cmd, _host, _port, _user, _password, _ssh_options: winrm_executor(
                    _cmd, _host, _port, _user, _password, _ssh_options, item_winrm_options
                )
            elif method == 'paramiko':
                ctx['ssh'] = lambda _cmd, _host, _port, _user, _password, _ssh_options: (
                    1,
                    '',
                    'paramiko connection method does not support _ssh; use _run_paramiko_commands',
                )
            else:
                ctx['ssh'] = lambda _cmd, _host, _port, _user, _password, _ssh_options: call_ssh_executor(
                    ssh_executor,
                    _cmd,
                    _host,
                    _port,
                    _user,
                    _password,
                    _ssh_options,
                    ssh_command_timeout_sec,
                )
        else:
            ctx['connection_method'] = 'none'

        try:
            item_type = getattr(mod, 'ITEM_TYPE', 'python')
            if item_type == 'shell':
                res = run_shell_item(mod, ctx)
            else:
                if hasattr(mod, 'CHECK_CLASS'):
                    res = mod.CHECK_CLASS(ctx).run()
                elif hasattr(mod, 'run'):
                    try:
                        res = mod.run(ctx)
                    except TypeError:
                        res = mod.run()
                else:
                    res = {'inspection_code': code, 'item_id': item_id, 'status': 'fail', 'error': 'no_runner'}
        except Exception as e:
            res = {
                'inspection_code': code,
                'item_id': item_id,
                'status': 'fail',
                'error': 'exec_error',
                'message': str(e),
                'raw_output': str(e),
            }

        if result_item_payload:
            res = {**result_item_payload, **res}
        results.append(res)
        summary = summarize_result(res)
        logger.info(
            '--- item done: inspection_code=%s status=%s error=%s reasons=%s raw_len=%s',
            code,
            summary.get('status'),
            summary.get('error'),
            summary.get('reasons'),
            summary.get('raw_len'),
        )
        if summary.get('message'):
            logger.info('    message=%s', summary.get('message'))
        if summary.get('metrics'):
            logger.info('    metrics=%s', summary.get('metrics'))
        if summary.get('raw_preview'):
            logger.info('    raw_preview=%s', summary.get('raw_preview'))
        logger.info('    result_json=\n%s', json.dumps(res, ensure_ascii=False, indent=2))
        if item_sleep_sec > 0 and idx < (len(items) - 1):
            time.sleep(item_sleep_sec)

    output = {
        'items': items,
        'results': results,
        'failed_items': [r.get('inspection_code') for r in results if r.get('status') == 'fail'],
    }
    logger.info('### Runner terminated. total=%s failed=%s', len(results), len(output['failed_items']))
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
