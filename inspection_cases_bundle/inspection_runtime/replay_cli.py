#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import logging
import os
import re
import sys

try:
    from .runner import execute_runner, run_no_ssh
except ImportError:
    from runner import execute_runner, run_no_ssh


def load_json(path):
    with open(path, 'r', encoding='utf-8') as fh:
        return json.load(fh)


def read_text(path):
    with open(path, 'r', encoding='utf-8') as fh:
        return fh.read()


MULTILINE_READABLE_KEYS = {
    'check_script',
    'message',
    'raw_output',
    'reasons',
    'stderr',
    'stdout',
}


def build_readable_json(data):
    if isinstance(data, list):
        return [build_readable_json(item) for item in data]

    if not isinstance(data, dict):
        return data

    readable = {}
    for key, value in data.items():
        readable[key] = build_readable_json(value)
        if key in MULTILINE_READABLE_KEYS and isinstance(value, str) and '\n' in value:
            readable[f'{key}_lines'] = value.splitlines()
    return readable


def write_json(path, data, readable_multiline=False):
    serialized = build_readable_json(data) if readable_multiline else data
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(serialized, fh, ensure_ascii=False, indent=2)
        fh.write('\n')


def is_case_dir(path):
    if not os.path.isdir(path):
        return False
    required = ('case.json', 'script.py', 'replay.json')
    return all(os.path.isfile(os.path.join(path, name)) for name in required)


def discover_case_dirs(path):
    abs_path = os.path.abspath(path)
    if is_case_dir(abs_path):
        return [abs_path], abs_path

    if not os.path.isdir(abs_path):
        raise ValueError(f'case path not found: {path}')

    case_dirs = []
    for current_dir, dir_names, _file_names in os.walk(abs_path):
        dir_names[:] = sorted(
            name
            for name in dir_names
            if not name.startswith('.') and name != '__pycache__'
        )

        if is_case_dir(current_dir):
            case_dirs.append(current_dir)
            dir_names[:] = []

    if not case_dirs:
        raise ValueError(f'no case directories found under: {path}')

    return case_dirs, abs_path


def load_case_payload(case_dir):
    case_path = os.path.join(case_dir, 'case.json')
    script_path = os.path.join(case_dir, 'script.py')
    replay_path = os.path.join(case_dir, 'replay.json')

    case_data = load_json(case_path)
    script_text = read_text(script_path)
    replay_rules = load_json(replay_path)

    item = case_data.get('item')
    if not isinstance(item, dict) or not item:
        raise ValueError(f'case item is required: {case_path}')

    payload = dict(case_data)
    payload.pop('item', None)
    item_payload = dict(item)
    item_payload['check_script'] = script_text
    payload['items'] = [item_payload]
    return payload, replay_rules


class ReplayCommandExecutor:
    def __init__(self, case_dir, rules):
        self.case_dir = case_dir
        self.rules = []
        self.position = 0
        self._load_rules(rules)

    def _load_rules(self, rules):
        if not isinstance(rules, list):
            raise ValueError('replay.json must contain a list')

        for idx, rule in enumerate(rules, 1):
            if not isinstance(rule, dict):
                raise ValueError(f'replay rule #{idx} must be an object')

            matcher_type = str(rule.get('matcher_type') or '').strip().lower()
            matcher_value = str(rule.get('matcher_value') or '')
            if matcher_type not in ('exact', 'contains', 'regex'):
                raise ValueError(f'invalid matcher_type in rule #{idx}: {matcher_type}')
            if not matcher_value:
                raise ValueError(f'matcher_value is required in rule #{idx}')

            normalized = {
                'matcher_type': matcher_type,
                'matcher_value': matcher_value,
                'rc': int(rule.get('rc', 0)),
                'stdout': self._resolve_stream(rule, idx, 'stdout'),
                'stderr': self._resolve_stream(rule, idx, 'stderr'),
            }
            self.rules.append(normalized)

    def _resolve_stream(self, rule, idx, stream_name):
        if stream_name in rule and rule.get(stream_name) is not None:
            return str(rule.get(stream_name))

        file_key = f'{stream_name}_file'
        rel_path = rule.get(file_key)
        if not rel_path:
            return ''

        file_path = os.path.join(self.case_dir, rel_path)
        if not os.path.isfile(file_path):
            raise ValueError(f'{file_key} not found in rule #{idx}: {rel_path}')
        return read_text(file_path)

    def _matches(self, rule, cmd):
        matcher_type = rule['matcher_type']
        matcher_value = rule['matcher_value']

        if matcher_type == 'exact':
            return cmd == matcher_value
        if matcher_type == 'contains':
            return matcher_value in cmd
        return re.search(matcher_value, cmd, re.MULTILINE) is not None

    def _build_miss(self, cmd, method):
        if self.position >= len(self.rules):
            return (1, '', f'REPLAY_MISS: unexpected {method} command: {cmd}')

        expected = self.rules[self.position]
        expected_text = f"{expected['matcher_type']}:{expected['matcher_value']}"
        return (1, '', f'REPLAY_MISS: expected {expected_text} but got {method} command: {cmd}')

    def _consume(self, cmd, method):
        if self.position >= len(self.rules):
            return self._build_miss(cmd, method)

        rule = self.rules[self.position]
        if not self._matches(rule, cmd):
            return self._build_miss(cmd, method)

        self.position += 1
        return rule['rc'], rule['stdout'], rule['stderr']

    def run_ssh(self, cmd, host, port, user, password, ssh_options, timeout_sec=None):
        return self._consume(cmd, 'ssh')

    def run_winrm(self, cmd, host, port, user, password, ssh_options, winrm_options=None):
        return self._consume(cmd, 'winrm')

    def run_no_ssh(self, cmd, host, port, user, password, ssh_options):
        return run_no_ssh(cmd, host, port, user, password, ssh_options)


def build_case_logger(case_name):
    logger = logging.getLogger(f'inspection_replay.{case_name}')
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if not logger.handlers:
        logger.addHandler(logging.NullHandler())
    return logger


def run_case(case_dir, case_name=None):
    if case_name is None:
        case_name = os.path.basename(os.path.abspath(case_dir))
    payload, replay_rules = load_case_payload(case_dir)
    executor = ReplayCommandExecutor(case_dir, replay_rules)
    logger = build_case_logger(case_name)
    output = execute_runner(
        payload,
        ssh_executor=executor.run_ssh,
        winrm_executor=executor.run_winrm,
        no_ssh_executor=executor.run_no_ssh,
        skip_precheck=True,
        logger=logger,
    )
    result_path = os.path.join(case_dir, 'result.json')
    write_json(result_path, output, readable_multiline=True)
    return {
        'case_name': case_name,
        'result_path': result_path,
        'output': output,
    }


def build_summary(case_results, root_dir):
    summary_cases = []
    failed_cases = []

    for result in case_results:
        rel_result_path = ''
        if result.get('result_path'):
            rel_result_path = os.path.relpath(result['result_path'], root_dir)

        entry = {
            'case_name': result['case_name'],
            'result_file': rel_result_path,
            'failed_items': result.get('failed_items', []),
            'is_success': bool(result.get('is_success')),
        }
        if result.get('error'):
            entry['error'] = result['error']

        summary_cases.append(entry)
        if not entry['is_success']:
            failed_cases.append(result['case_name'])

    return {
        'total_cases': len(summary_cases),
        'failed_cases': failed_cases,
        'cases': summary_cases,
    }


def run_path(path):
    case_dirs, root_dir = discover_case_dirs(path)

    if len(case_dirs) == 1 and os.path.abspath(case_dirs[0]) == os.path.abspath(root_dir):
        case_result = run_case(case_dirs[0])
        return case_result['output'], 0

    aggregated = []
    for case_dir in case_dirs:
        case_name = os.path.relpath(case_dir, root_dir)
        try:
            result = run_case(case_dir, case_name=case_name)
            failed_items = result['output'].get('failed_items') or []
            aggregated.append({
                'case_name': case_name,
                'result_path': result['result_path'],
                'failed_items': failed_items,
                'is_success': not failed_items,
            })
        except Exception as exc:
            aggregated.append({
                'case_name': case_name,
                'result_path': '',
                'failed_items': [],
                'is_success': False,
                'error': str(exc),
            })

    summary = build_summary(aggregated, root_dir)
    summary_path = os.path.join(root_dir, 'summary.json')
    write_json(summary_path, summary)
    return summary, 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='Replay inspection runner payloads from local case directories.',
    )
    parser.add_argument('path', help='Case directory or root directory containing case subdirectories')
    args = parser.parse_args(argv)

    try:
        output, exit_code = run_path(args.path)
    except Exception as exc:
        print(json.dumps({'error': str(exc)}, ensure_ascii=False))
        return 1

    print(json.dumps(build_readable_json(output), ensure_ascii=False, indent=2))
    return exit_code


if __name__ == '__main__':
    sys.exit(main())
