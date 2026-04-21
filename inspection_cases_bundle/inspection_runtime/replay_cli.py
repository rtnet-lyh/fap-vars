#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import copy
import json
import logging
import os
import re
import sys

try:
    from .runner import execute_runner, run_no_ssh
    from .terminal import TerminalSession
except ImportError:
    from runner import execute_runner, run_no_ssh
    from terminal import TerminalSession


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


def load_case_data(case_dir):
    case_path = os.path.join(case_dir, 'case.json')
    case_data = load_json(case_path)
    if not isinstance(case_data, dict):
        raise ValueError(f'case.json must contain an object: {case_path}')
    return case_data


def load_script_text(case_dir):
    script_path = os.path.join(case_dir, 'script.py')
    return read_text(script_path)


def load_replay_rules(case_dir):
    replay_path = os.path.join(case_dir, 'replay.json')
    return load_json(replay_path)


def build_runner_payload(case_data, script_text, case_path):
    payload = dict(case_data or {})
    raw_items = payload.pop('items', None)
    if raw_items is None:
        item = payload.pop('item', None)
        if not isinstance(item, dict) or not item:
            raise ValueError(f'case item is required: {case_path}')
        raw_items = [item]

    if not isinstance(raw_items, list) or not raw_items:
        raise ValueError(f'case items are required: {case_path}')

    items = []
    for idx, item in enumerate(raw_items, 1):
        if not isinstance(item, dict) or not item:
            raise ValueError(f'case item #{idx} must be an object: {case_path}')
        item_payload = dict(item)
        item_payload['check_script'] = script_text
        items.append(item_payload)

    payload['items'] = items
    return payload


def load_case_payload(case_dir):
    case_path = os.path.join(case_dir, 'case.json')
    case_data = load_case_data(case_dir)
    script_text = load_script_text(case_dir)
    return build_runner_payload(case_data, script_text, case_path)


def deep_merge(base, override):
    if isinstance(base, dict) and isinstance(override, dict):
        merged = {key: copy.deepcopy(value) for key, value in base.items()}
        for key, value in override.items():
            if key in merged:
                merged[key] = deep_merge(merged[key], value)
            else:
                merged[key] = copy.deepcopy(value)
        return merged
    return copy.deepcopy(override)


def load_override_data(path):
    override_data = load_json(path)
    if not isinstance(override_data, dict):
        raise ValueError(f'override file must contain an object: {path}')
    return override_data


def has_any_credentials(credentials_map):
    if not isinstance(credentials_map, dict):
        return False
    for entries in credentials_map.values():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if isinstance(entry, dict):
                return True
    return False


def validate_live_payload(payload):
    host = str(payload.get('host') or '').strip()
    if not host:
        raise ValueError('live mode requires host in case.json or override file')

    user = str(payload.get('user') or '').strip()
    if not user and not has_any_credentials(payload.get('credentials')):
        raise ValueError('live mode requires credentials or user in case.json or override file')


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

            channel = str(rule.get('channel') or '').strip().lower()
            if channel == 'terminal':
                action = str(rule.get('action') or '').strip().lower()
                if action not in ('open', 'send', 'recv', 'close'):
                    raise ValueError(f'invalid terminal action in rule #{idx}: {action}')

                normalized = {
                    'channel': 'terminal',
                    'action': action,
                    'matcher_type': str(rule.get('matcher_type') or 'exact').strip().lower(),
                    'matcher_value': str(rule.get('matcher_value') or rule.get('value') or ''),
                    'redacted': bool(rule.get('redacted')),
                    'stdout': self._resolve_stream(rule, idx, 'stdout'),
                }

                if action == 'send' and not normalized['redacted'] and not normalized['matcher_value']:
                    raise ValueError(f'matcher_value is required in terminal send rule #{idx}')
                if normalized['matcher_type'] not in ('exact', 'contains', 'regex'):
                    raise ValueError(f'invalid matcher_type in terminal rule #{idx}: {normalized["matcher_type"]}')

                self.rules.append(normalized)
                continue

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

    def _peek_rule(self):
        if self.position >= len(self.rules):
            return None
        return self.rules[self.position]

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

    def _consume_terminal_open(self):
        rule = self._peek_rule()
        if not rule or rule.get('channel') != 'terminal' or rule.get('action') != 'open':
            return None
        self.position += 1
        return rule.get('stdout', '')

    def _consume_terminal_close(self):
        rule = self._peek_rule()
        if not rule or rule.get('channel') != 'terminal' or rule.get('action') != 'close':
            return
        self.position += 1

    def _consume_terminal_send(self, text, redacted=False):
        rule = self._peek_rule()
        if not rule:
            raise ValueError(f'REPLAY_MISS: unexpected terminal send: {text}')
        if rule.get('channel') != 'terminal' or rule.get('action') != 'send':
            raise ValueError(
                f'REPLAY_MISS: expected terminal {rule.get("action")} but got terminal send: {text}'
            )
        if bool(rule.get('redacted')) != bool(redacted):
            raise ValueError(
                f'REPLAY_MISS: terminal send redaction mismatch for: {text}'
            )
        if not rule.get('redacted') and not self._matches(rule, text):
            expected_text = f"{rule['matcher_type']}:{rule['matcher_value']}"
            raise ValueError(f'REPLAY_MISS: expected terminal send {expected_text} but got: {text}')
        self.position += 1

    def _consume_terminal_recv(self, allow_no_data=False):
        rule = self._peek_rule()
        if not rule:
            if allow_no_data:
                return None
            return ''
        if rule.get('channel') == 'terminal' and rule.get('action') == 'close':
            self.position += 1
            return ''
        if rule.get('channel') != 'terminal' or rule.get('action') != 'recv':
            if allow_no_data:
                return None
            raise ValueError(
                f'REPLAY_MISS: expected terminal {rule.get("action")} but got terminal recv'
            )
        self.position += 1
        return rule.get('stdout', '')

    def run_ssh(self, cmd, host, port, user, password, ssh_options, timeout_sec=None):
        return self._consume(cmd, 'ssh')

    def run_winrm(self, cmd, host, port, user, password, ssh_options, winrm_options=None):
        return self._consume(cmd, 'winrm')

    def run_no_ssh(self, cmd, host, port, user, password, ssh_options):
        return run_no_ssh(cmd, host, port, user, password, ssh_options)

    def open_terminal(
        self,
        host,
        port,
        user,
        password,
        ssh_options,
        history_callback=None,
        pager_patterns=None,
        pager_response=' ',
        preferred_encodings=None,
        open_timeout_sec=None,
        default_timeout_sec=None,
    ):
        transport = ReplayTerminalTransport(self)
        return TerminalSession(
            transport=transport,
            history_callback=history_callback,
            pager_patterns=pager_patterns,
            pager_response=pager_response,
            default_timeout_sec=default_timeout_sec,
        )


class ReplayTerminalTransport:
    def __init__(self, executor):
        self.executor = executor
        self.closed = False
        self.prefetched = executor._consume_terminal_open()

    def send(self, text, newline=False, redacted=False):
        del newline
        self.executor._consume_terminal_send(str(text or ''), redacted=redacted)

    def read_chunk(self, timeout_sec=None):
        if self.closed:
            return ''
        if self.prefetched is not None:
            data = self.prefetched
            self.prefetched = None
            return data
        data = self.executor._consume_terminal_recv(allow_no_data=timeout_sec is not None)
        if data == '':
            self.closed = True
        return data

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.executor._consume_terminal_close()


def build_case_logger(case_name):
    logger = logging.getLogger(f'inspection_replay.{case_name}')
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if not logger.handlers:
        logger.addHandler(logging.NullHandler())
    return logger


def run_case_replay(case_dir, case_name=None):
    if case_name is None:
        case_name = os.path.basename(os.path.abspath(case_dir))
    payload = load_case_payload(case_dir)
    replay_rules = load_replay_rules(case_dir)
    executor = ReplayCommandExecutor(case_dir, replay_rules)
    logger = build_case_logger(case_name)
    output = execute_runner(
        payload,
        ssh_executor=executor.run_ssh,
        winrm_executor=executor.run_winrm,
        no_ssh_executor=executor.run_no_ssh,
        terminal_opener=executor.open_terminal,
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


def run_case_live(case_dir, override_file, case_name=None):
    if case_name is None:
        case_name = os.path.basename(os.path.abspath(case_dir))

    case_path = os.path.join(case_dir, 'case.json')
    case_data = load_case_data(case_dir)
    merged_case_data = case_data
    if override_file:
        override_data = load_override_data(override_file)
        merged_case_data = deep_merge(case_data, override_data)
    script_text = load_script_text(case_dir)
    payload = build_runner_payload(merged_case_data, script_text, case_path)
    validate_live_payload(payload)

    logger = build_case_logger(case_name)
    output = execute_runner(payload, logger=logger)
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


def run_path(path, mode='replay', override_file=None):
    if mode not in ('replay', 'live'):
        raise ValueError(f'unsupported mode: {mode}')

    if mode != 'live' and override_file:
        raise ValueError('--override-file is only supported in live mode')

    if mode == 'live':
        case_dir = os.path.abspath(path)
        if not is_case_dir(case_dir):
            raise ValueError(f'live mode requires a single case directory: {path}')
        case_result = run_case_live(case_dir, override_file=override_file)
        return case_result['output'], 0

    case_dirs, root_dir = discover_case_dirs(path)

    if len(case_dirs) == 1 and os.path.abspath(case_dirs[0]) == os.path.abspath(root_dir):
        case_result = run_case_replay(case_dirs[0])
        return case_result['output'], 0

    aggregated = []
    for case_dir in case_dirs:
        case_name = os.path.relpath(case_dir, root_dir)
        try:
            result = run_case_replay(case_dir, case_name=case_name)
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
    parser.add_argument(
        '--mode',
        choices=('replay', 'live'),
        default='replay',
        help='Execution mode. replay uses replay.json fixtures, live uses case.json and optionally merges an override JSON file.',
    )
    parser.add_argument(
        '--override-file',
        help='Optional JSON file containing live-mode overrides for case.json values such as host, credentials, thresholds, and item.',
    )
    args = parser.parse_args(argv)

    try:
        output, exit_code = run_path(
            args.path,
            mode=args.mode,
            override_file=args.override_file,
        )
    except Exception as exc:
        print(json.dumps({'error': str(exc)}, ensure_ascii=False))
        return 1

    print(json.dumps(build_readable_json(output), ensure_ascii=False, indent=2))
    return exit_code


if __name__ == '__main__':
    sys.exit(main())
