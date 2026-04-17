#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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


def coerce_text(value):
    if value is None:
        return value
    if isinstance(value, bytes):
        return value.decode('utf-8', 'ignore')
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
            db_error = str(exc)
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
            resp = session.run_ps(cmd)
        out = strip_runtime_warnings((resp.std_out or b'').decode('utf-8', 'ignore'))
        err = strip_runtime_warnings((resp.std_err or b'').decode('utf-8', 'ignore'))
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
    if not skip_precheck:
        for it in items:
            code, _, item_payload = normalize_item(it)
            lookup_payload = build_lookup_payload(code, item_payload)
            mod, module_key, module_source, db_error = resolve_runtime_item_module(available, lookup_payload, logger)
            if not mod or not needs_host_connection(mod):
                continue
            method = get_connection_method(mod, lookup_payload)
            if method in checked_methods or method in precheck_errors:
                continue
            connection_credential = select_connection_credential(credentials, method, lookup_payload)
            connection_values = resolve_connection_values(port, method, connection_credential, user, password)
            if method == 'winrm':
                shell = getattr(mod, 'WINRM_SHELL', None)
                if shell is None and hasattr(mod, 'CHECK_CLASS'):
                    shell = getattr(mod.CHECK_CLASS, 'WINRM_SHELL', None)
                wr_opts = dict(winrm_options)
                if shell:
                    wr_opts['shell'] = shell
                rc, out, err = winrm_executor(
                    'Write-Output FAP_CONNECTION_OK',
                    host,
                    connection_values.get('port'),
                    connection_values.get('user'),
                    connection_values.get('password'),
                    ssh_options,
                    wr_opts,
                )
            else:
                rc, out, err = call_ssh_executor(
                    ssh_executor,
                    'true',
                    host,
                    connection_values.get('port'),
                    connection_values.get('user'),
                    connection_values.get('password'),
                    ssh_options,
                    DEFAULT_SSH_COMMAND_TIMEOUT_SEC,
                )
            if rc != 0:
                precheck_errors[method] = (err or out or '').strip() or '연결 실패'
                logger.error(
                    'host precheck failed: method=%s inspection_code=%s application_type=%s application=%s message=%s',
                    method,
                    module_key[0] if module_key else code,
                    module_key[1] if module_key else COMMON_TOKEN,
                    module_key[2] if module_key else COMMON_TOKEN,
                    precheck_errors[method],
                )
                continue
            checked_methods.add(method)
            logger.info(
                'host precheck ok: method=%s source=%s inspection_code=%s application_type=%s application=%s',
                method,
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
        if method in precheck_errors:
            res = build_precheck_fail_result(code, item_id, item_payload, method, precheck_errors[method])
            results.append(res)
            logger.info('    result_json=\n%s', json.dumps(res, ensure_ascii=False, indent=2))
            continue
        if not mod:
            # 요청한 항목이 없으면 실패로 기록
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
        }
        logger.info("created ctx:\n%s", json.dumps(ctx, ensure_ascii=False, indent=2, default=str))
        if needs_host_connection(mod):
            ctx['connection_method'] = method
            if method == 'winrm':
                shell = getattr(mod, 'WINRM_SHELL', None)
                if shell is None and hasattr(mod, 'CHECK_CLASS'):
                    shell = getattr(mod.CHECK_CLASS, 'WINRM_SHELL', None)
                wr_opts = dict(winrm_options)
                if shell:
                    wr_opts['shell'] = shell
                ctx['ssh'] = lambda _cmd, _host, _port, _user, _password, _ssh_options: winrm_executor(
                    _cmd, _host, _port, _user, _password, _ssh_options, wr_opts
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
