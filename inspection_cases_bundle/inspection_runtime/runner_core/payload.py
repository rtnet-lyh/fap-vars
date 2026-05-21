# -*- coding: utf-8 -*-
"""Payload and item normalization helpers for inspection runner.

This module intentionally contains only small pure helpers extracted from
``runner.py``. Keep behavior byte-for-byte compatible with the runner wrappers.
"""


def sanitize_item_payload(item_payload):
    if not item_payload:
        return {}
    sanitized = dict(item_payload)
    sanitized.pop('inspection_script', None)
    sanitized.pop('check_script', None)
    return sanitized


def normalize_item(it):
    if isinstance(it, dict):
        return it.get('inspection_code'), it.get('item_id'), it
    return it, None, {}


def build_lookup_payload(code, item_payload):
    lookup_payload = {'inspection_code': code}
    if item_payload:
        lookup_payload.update(item_payload)
    return lookup_payload
