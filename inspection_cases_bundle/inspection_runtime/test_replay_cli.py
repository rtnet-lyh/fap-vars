#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import sys
import tempfile
import unittest
from unittest import mock


CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

import replay_cli


SCRIPT_TEXT = """# -*- coding: utf-8 -*-

from .common._base import BaseCheck


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def run(self):
        rc, out, err = self._ssh("echo hello")
        if rc != 0:
            return self.fail(
                'command failed',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )
        expected = self.get_threshold_var('expected', default='missing')
        return self.ok(
            metrics={'expected': expected},
            thresholds={'expected': expected},
            reasons='ok',
            raw_output=(out or '').strip(),
            message='ok',
        )


CHECK_CLASS = Check
"""

TERMINAL_SCRIPT_TEXT = """# -*- coding: utf-8 -*-

from .common._base import BaseCheck


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def run(self):
        with self._open_terminal(
            pager_patterns=[r'--More--'],
            pager_response=' ',
        ) as term:
            prompt = term.expect([r'>\\s*$', r'#\\s*$'])
            if prompt.index == 0:
                term.sendline('enable')
                term.expect([r'Password:\\s*$'])
                term.sendline(self.get_connection_value('en_password'), redact=True)
                term.expect([r'#\\s*$'])

            term.sendline('terminal length 0')
            term.expect([r'#\\s*$'])
            output = term.run('show running-config', [r'#\\s*$'])

        if 'Current configuration' not in output:
            return self.fail(
                'config missing',
                stdout=output,
            )

        return self.ok(
            metrics={'has_config': True},
            reasons='ok',
            message='terminal ok',
        )


CHECK_CLASS = Check
"""

LOOSE_TERMINAL_SCRIPT_TEXT = """# -*- coding: utf-8 -*-

from .common._base import BaseCheck


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def run(self):
        with self._open_terminal(default_timeout_sec=0.01) as term:
            term.sendline('first')
            timeout_result = term.expect([r'NEVER_MATCHES'])
            term.sendline('second')
            done_result = term.expect([r'DONE'])

        if timeout_result.matched or not timeout_result.timed_out:
            return self.fail('timeout result mismatch', stdout=timeout_result.text)
        if not done_result.matched:
            return self.fail('done missing', stdout=done_result.text)

        return self.ok(
            metrics={'timeout_continued': True},
            reasons='ok',
            message='loose terminal ok',
        )


CHECK_CLASS = Check
"""

SYNTAX_ERROR_SCRIPT_TEXT = """# -*- coding: utf-8 -*-

from .common._base import BaseCheck


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def run(self):
        result = self._ssh("broken)
        return self.ok(message='ok')


CHECK_CLASS = Check
"""

IMPORT_ERROR_SCRIPT_TEXT = """# -*- coding: utf-8 -*-

import missing_module_for_live_test

from .common._base import BaseCheck


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def run(self):
        return self.ok(message='ok')


CHECK_CLASS = Check
"""


class ReplayCliTest(unittest.TestCase):
    def create_case_dir(self, root_dir, name='case_a'):
        case_dir = os.path.join(root_dir, name)
        os.makedirs(case_dir, exist_ok=True)

        case_data = {
            'host': '127.0.0.1',
            'port': 22,
            'user': 'root',
            'password': '',
            'credentials': {
                'LINUX': [
                    {
                        'application_type_name': 'LINUX',
                        'credential_type_name': 'SSH',
                        'data': {
                            'username': 'root',
                            'password': '',
                        },
                    }
                ]
            },
            'thresholds': {},
            'item_sleep_sec': 0,
            'execution_id': 1,
            'host_id': 10,
            'job_id': 100,
            'item': {
                'inspection_code': 'U-TEST-01',
                'item_id': 90001,
                'application_type_name': 'LINUX',
                'threshold_list': [
                    {
                        'name': 'expected',
                        'value1': 'base',
                    }
                ],
            },
        }
        replay_rules = [
            {
                'matcher_type': 'exact',
                'matcher_value': 'echo hello',
                'rc': 0,
                'stdout': 'hello\n',
                'stderr': '',
            }
        ]

        with open(os.path.join(case_dir, 'case.json'), 'w', encoding='utf-8') as fh:
            json.dump(case_data, fh, ensure_ascii=False, indent=2)
            fh.write('\n')
        with open(os.path.join(case_dir, 'script.py'), 'w', encoding='utf-8') as fh:
            fh.write(SCRIPT_TEXT)
        with open(os.path.join(case_dir, 'replay.json'), 'w', encoding='utf-8') as fh:
            json.dump(replay_rules, fh, ensure_ascii=False, indent=2)
            fh.write('\n')

        return case_dir

    def create_terminal_case_dir(self, root_dir, name='terminal_case'):
        case_dir = os.path.join(root_dir, name)
        os.makedirs(case_dir, exist_ok=True)

        case_data = {
            'host': '127.0.0.1',
            'port': 22,
            'user': 'admin',
            'password': 'admin',
            'credentials': {
                'NETWORK': [
                    {
                        'application_type_name': 'NETWORK',
                        'credential_type_name': 'NETWORK_DEVICE',
                        'data': {
                            'username': 'admin',
                            'password': 'admin',
                            'en_password': 'secret',
                        },
                    }
                ]
            },
            'thresholds': {},
            'item_sleep_sec': 0,
            'execution_id': 2,
            'host_id': 20,
            'job_id': 200,
            'item': {
                'inspection_code': 'N-TEST-TERM-01',
                'item_id': 90002,
                'application_type_name': 'NETWORK',
                'threshold_list': [],
            },
        }
        replay_rules = [
            {'channel': 'terminal', 'action': 'recv', 'stdout': 'Router>'},
            {'channel': 'terminal', 'action': 'send', 'matcher_value': 'enable'},
            {'channel': 'terminal', 'action': 'recv', 'stdout': 'Password:'},
            {'channel': 'terminal', 'action': 'send', 'redacted': True},
            {'channel': 'terminal', 'action': 'recv', 'stdout': 'Router#'},
            {'channel': 'terminal', 'action': 'send', 'matcher_value': 'terminal length 0'},
            {'channel': 'terminal', 'action': 'recv', 'stdout': 'Router#'},
            {'channel': 'terminal', 'action': 'send', 'matcher_value': 'show running-config'},
            {'channel': 'terminal', 'action': 'recv', 'stdout': 'show running-config\r\nCurrent configuration : 123\r\n--More--'},
            {'channel': 'terminal', 'action': 'send', 'matcher_value': ' '},
            {'channel': 'terminal', 'action': 'recv', 'stdout': '\r\nhostname TEST_ROUTER\r\nRouter#'},
        ]

        with open(os.path.join(case_dir, 'case.json'), 'w', encoding='utf-8') as fh:
            json.dump(case_data, fh, ensure_ascii=False, indent=2)
            fh.write('\n')
        with open(os.path.join(case_dir, 'script.py'), 'w', encoding='utf-8') as fh:
            fh.write(TERMINAL_SCRIPT_TEXT)
        with open(os.path.join(case_dir, 'replay.json'), 'w', encoding='utf-8') as fh:
            json.dump(replay_rules, fh, ensure_ascii=False, indent=2)
            fh.write('\n')

        return case_dir

    def test_run_path_replay_uses_replay_rules(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            case_dir = self.create_case_dir(tmp_dir)

            output, exit_code = replay_cli.run_path(case_dir, mode='replay')

            self.assertEqual(exit_code, 0)
            self.assertEqual(output['failed_items'], [])
            self.assertEqual(output['results'][0]['status'], 'ok')
            self.assertEqual(output['results'][0]['metrics']['expected'], 'base')

            result_path = os.path.join(case_dir, 'result.json')
            self.assertTrue(os.path.isfile(result_path))

    def test_run_path_live_uses_case_json_without_override(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            case_dir = self.create_case_dir(tmp_dir)
            captured = {}

            def fake_execute_runner(payload, **kwargs):
                captured['payload'] = payload
                return {
                    'items': payload.get('items', []),
                    'results': [
                        {
                            'inspection_code': payload['items'][0]['inspection_code'],
                            'status': 'ok',
                            'metrics': {
                                'expected': payload['items'][0]['threshold_list'][0]['value1'],
                            },
                            'message': 'live ok',
                            'raw_output': 'live ok',
                        }
                    ],
                    'failed_items': [],
                }

            with mock.patch.object(replay_cli, 'execute_runner', side_effect=fake_execute_runner):
                output, exit_code = replay_cli.run_path(case_dir, mode='live')

            self.assertEqual(exit_code, 0)
            self.assertEqual(output['failed_items'], [])
            self.assertEqual(captured['payload']['host'], '127.0.0.1')
            self.assertEqual(
                captured['payload']['credentials']['LINUX'][0]['data']['username'],
                'root',
            )
            self.assertEqual(
                captured['payload']['items'][0]['threshold_list'],
                [{'name': 'expected', 'value1': 'base'}],
            )

    def test_run_path_live_merges_override_and_replaces_lists(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            case_dir = self.create_case_dir(tmp_dir)
            override_path = os.path.join(tmp_dir, 'override.json')
            with open(override_path, 'w', encoding='utf-8') as fh:
                json.dump(
                    {
                        'host': '10.0.0.10',
                        'credentials': {
                            'LINUX': [
                                {
                                    'application_type_name': 'LINUX',
                                    'credential_type_name': 'SSH',
                                    'data': {
                                        'username': 'inspector',
                                        'password': 'secret',
                                    },
                                }
                            ]
                        },
                        'item': {
                            'threshold_list': [
                                {
                                    'name': 'expected',
                                    'value1': 'override',
                                }
                            ]
                        },
                    },
                    fh,
                    ensure_ascii=False,
                    indent=2,
                )
                fh.write('\n')

            captured = {}

            def fake_execute_runner(payload, **kwargs):
                captured['payload'] = payload
                return {
                    'items': payload.get('items', []),
                    'results': [
                        {
                            'inspection_code': payload['items'][0]['inspection_code'],
                            'status': 'ok',
                            'metrics': {
                                'expected': payload['items'][0]['threshold_list'][0]['value1'],
                            },
                            'message': 'live ok',
                            'raw_output': 'live ok',
                        }
                    ],
                    'failed_items': [],
                }

            with mock.patch.object(replay_cli, 'execute_runner', side_effect=fake_execute_runner):
                output, exit_code = replay_cli.run_path(
                    case_dir,
                    mode='live',
                    override_file=override_path,
                )

            self.assertEqual(exit_code, 0)
            self.assertEqual(output['failed_items'], [])
            self.assertEqual(captured['payload']['host'], '10.0.0.10')
            self.assertEqual(
                captured['payload']['credentials']['LINUX'][0]['data']['username'],
                'inspector',
            )
            self.assertEqual(
                captured['payload']['items'][0]['threshold_list'],
                [{'name': 'expected', 'value1': 'override'}],
            )
            self.assertIn('check_script', captured['payload']['items'][0])

            result_path = os.path.join(case_dir, 'result.json')
            self.assertTrue(os.path.isfile(result_path))

    def test_run_path_live_surfaces_python_syntax_error_text(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            case_dir = self.create_case_dir(tmp_dir, name='syntax_error_case')
            with open(os.path.join(case_dir, 'script.py'), 'w', encoding='utf-8') as fh:
                fh.write(SYNTAX_ERROR_SCRIPT_TEXT)

            output, exit_code = replay_cli.run_path(case_dir, mode='live')

            self.assertEqual(exit_code, 0)
            self.assertEqual(output['failed_items'], ['U-TEST-01'])
            self.assertEqual(output['results'][0]['status'], 'fail')
            self.assertEqual(output['results'][0]['error'], 'script_load_error')
            self.assertIn('SyntaxError:', output['results'][0]['message'])
            self.assertEqual(output['results'][0]['message'], output['results'][0]['raw_output'])

    def test_run_path_live_surfaces_python_import_error_text(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            case_dir = self.create_case_dir(tmp_dir, name='import_error_case')
            with open(os.path.join(case_dir, 'script.py'), 'w', encoding='utf-8') as fh:
                fh.write(IMPORT_ERROR_SCRIPT_TEXT)

            output, exit_code = replay_cli.run_path(case_dir, mode='live')

            self.assertEqual(exit_code, 0)
            self.assertEqual(output['failed_items'], ['U-TEST-01'])
            self.assertEqual(output['results'][0]['status'], 'fail')
            self.assertEqual(output['results'][0]['error'], 'script_load_error')
            self.assertIn('ModuleNotFoundError:', output['results'][0]['message'])
            self.assertEqual(output['results'][0]['message'], output['results'][0]['raw_output'])

    def test_live_mode_rejects_directory_batch_path(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            self.create_case_dir(tmp_dir, name='case_a')
            override_path = os.path.join(tmp_dir, 'override.json')
            with open(override_path, 'w', encoding='utf-8') as fh:
                json.dump({'host': '10.0.0.10'}, fh, ensure_ascii=False, indent=2)
                fh.write('\n')

            with self.assertRaisesRegex(ValueError, 'single case directory'):
                replay_cli.run_path(
                    tmp_dir,
                    mode='live',
                    override_file=override_path,
                )

    def test_override_file_is_rejected_in_replay_mode(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            case_dir = self.create_case_dir(tmp_dir)
            override_path = os.path.join(tmp_dir, 'override.json')
            with open(override_path, 'w', encoding='utf-8') as fh:
                json.dump({'host': '10.0.0.10'}, fh, ensure_ascii=False, indent=2)
                fh.write('\n')

            with self.assertRaisesRegex(ValueError, 'only supported in live mode'):
                replay_cli.run_path(
                    case_dir,
                    mode='replay',
                    override_file=override_path,
                )

    def test_run_path_replay_supports_terminal_events(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            case_dir = self.create_terminal_case_dir(tmp_dir)

            output, exit_code = replay_cli.run_path(case_dir, mode='replay')

            self.assertEqual(exit_code, 0)
            self.assertEqual(output['failed_items'], [])
            self.assertEqual(output['results'][0]['status'], 'ok')
            self.assertTrue(output['results'][0]['metrics']['has_config'])
            self.assertIn('터미널 송신: enable', output['results'][0]['raw_output'])
            self.assertIn('자동 응답', output['results'][0]['raw_output'])

    def test_run_path_replay_allows_terminal_expect_timeout_between_sends(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            case_dir = self.create_terminal_case_dir(tmp_dir, name='loose_terminal_case')
            replay_rules = [
                {'channel': 'terminal', 'action': 'send', 'matcher_value': 'first'},
                {'channel': 'terminal', 'action': 'send', 'matcher_value': 'second'},
                {'channel': 'terminal', 'action': 'recv', 'stdout': 'DONE'},
            ]

            with open(os.path.join(case_dir, 'script.py'), 'w', encoding='utf-8') as fh:
                fh.write(LOOSE_TERMINAL_SCRIPT_TEXT)
            with open(os.path.join(case_dir, 'replay.json'), 'w', encoding='utf-8') as fh:
                json.dump(replay_rules, fh, ensure_ascii=False, indent=2)
                fh.write('\n')

            output, exit_code = replay_cli.run_path(case_dir, mode='replay')

            self.assertEqual(exit_code, 0)
            self.assertEqual(output['failed_items'], [])
            self.assertEqual(output['results'][0]['status'], 'ok')
            self.assertTrue(output['results'][0]['metrics']['timeout_continued'])
            self.assertIn('터미널 수신(timeout)', output['results'][0]['raw_output'])


if __name__ == '__main__':
    unittest.main()
