# -*- coding: utf-8 -*-
"""Result summary and result builder helpers for inspection runner.

This module intentionally contains only small helpers extracted from
``runner.py``. Keep result dict structure, strings, fallback behavior, and
merge order compatible with the runner wrappers.
"""

from items.common.utils.command_result import summarize_raw_output
from runner_core.payload import sanitize_item_payload


def summarize_result(res):
    # 로그에 넣기 좋은 요약 (원문 전체 로그 방지)
    status = res.get('status')
    error = res.get('error')
    message = res.get('message') or ''
    reasons = res.get('reasons')
    metrics = res.get('metrics')
    raw_output = res.get('raw_output')
    raw_len, raw_preview = summarize_raw_output(raw_output)
    return {
        'status': status,
        'error': error,
        'message': message,
        'reasons': reasons,
        'metrics': metrics,
        'raw_len': raw_len,
        'raw_preview': raw_preview,
    }


def build_runner_output(items, results):
    return {
        'items': items,
        'results': results,
        'failed_items': [r.get('inspection_code') for r in results if r.get('status') == 'fail'],
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

def build_missing_item_result(code, item_id, result_item_payload, db_error):
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
    return res


def build_no_runner_result(code, item_id):
    return {'inspection_code': code, 'item_id': item_id, 'status': 'fail', 'error': 'no_runner'}


def build_exec_error_result(code, item_id, exc):
    return {
        'inspection_code': code,
        'item_id': item_id,
        'status': 'fail',
        'error': 'exec_error',
        'message': str(exc),
        'raw_output': str(exc),
    }

