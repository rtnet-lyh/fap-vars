# -*- coding: utf-8 -*-

"""Credential lookup helper utilities.

These helpers are intentionally small and side-effect free.  Runner-level
selection policy and BaseCheck public APIs keep their existing wrapper names.
"""


def normalize_credential_key(value):
    """Normalize credential map keys and type names for comparison."""
    if value is None:
        return ''
    return str(value).strip().upper()


def credential_or_empty(credential):
    """Return a credential mapping when it is a dict, otherwise an empty dict."""
    if isinstance(credential, dict):
        return credential
    return {}


def credential_data_or_empty(credential):
    """Return credential['data'] when it is a dict, otherwise an empty dict."""
    credential = credential_or_empty(credential)
    data = credential.get('data') or {}
    if isinstance(data, dict):
        return data
    return {}


def credential_context_data(ctx, context_key, fallback_credential=None):
    """Return a credential data dict from ctx, with optional credential fallback."""
    if isinstance(ctx, dict):
        data = ctx.get(context_key) or {}
        if isinstance(data, dict):
            return data
    return credential_data_or_empty(fallback_credential)


def credential_value(data, key, default=None):
    """Read a credential value from a data mapping with the legacy default rule."""
    if not isinstance(data, dict):
        return default
    return data.get(key, default)


def preferred_credential_value(application_data, connection_data, key, default=None):
    """Return application credential value first, then connection credential value.

    Only None and the empty string are treated as empty.  Values such as False
    and 0 are valid credential values and must be preserved.
    """
    for data in (application_data, connection_data):
        if not isinstance(data, dict) or key not in data:
            continue
        value = data.get(key)
        if value not in (None, ''):
            return value
    return default


def flatten_credentials(credentials_map):
    """Flatten credential buckets while preserving runner selection semantics."""
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


def filter_credentials(entries, credential_types=None, application_types=None):
    """Filter flattened credential entries by normalized credential/application types."""
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


def pick_credential(entries, application_id=None, application_type_id=None):
    """Pick a credential by application id, then application type id, then first entry."""
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


def select_application_credential(credentials_map, item_payload):
    """Select application credential while preserving runner policy semantics."""
    item_payload = item_payload or {}
    credentials_map = credentials_map or {}

    application_type_name = normalize_credential_key(item_payload.get('application_type_name'))
    application_type_id = item_payload.get('application_type_id')
    application_id = item_payload.get('application_id')

    candidates = []
    if application_type_name:
        candidates = credentials_map.get(application_type_name) or []

    selected = pick_credential(
        candidates,
        application_id=application_id,
        application_type_id=application_type_id,
    )
    if selected:
        return selected

    for key, entries in credentials_map.items():
        if application_type_name and normalize_credential_key(key) != application_type_name:
            continue
        selected = pick_credential(
            entries,
            application_id=application_id,
            application_type_id=application_type_id,
        )
        if selected:
            return selected

    if application_type_id is None and application_id is None:
        return None

    for entries in credentials_map.values():
        selected = pick_credential(
            entries,
            application_id=application_id,
            application_type_id=application_type_id,
        )
        if selected:
            return selected

    return None

