import hashlib
import importlib
import os
import re
import sys
import traceback
import types
from functools import lru_cache

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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
