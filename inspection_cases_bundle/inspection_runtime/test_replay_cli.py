#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import io
import os
import socket
import sys
import tempfile
import unittest
from unittest import mock


CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

import replay_cli
import runner
from items.common._base import BaseCheck


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

SSH_BECOME_SCRIPT_TEXT = """# -*- coding: utf-8 -*-

from .common._base import BaseCheck


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def run(self):
        rc, out, err = self._ssh("id -un", become=True)
        if rc != 0:
            return self.fail(
                'command failed',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )
        return self.ok(
            metrics={'user': (out or '').strip()},
            thresholds={},
            reasons='ok',
            message='become ok',
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

PARAMIKO_SCRIPT_TEXT = """# -*- coding: utf-8 -*-

from .common._base import BaseCheck


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'cisco_ios'
    PARAMIKO_ENABLE_MODE = True
    PARAMIKO_AUTH_METHOD = 'password'

    def run(self):
        results = self._run_paramiko_commands([
            'terminal length 0',
            'show version',
        ])
        failed = [item for item in results if item['rc'] != 0]
        if failed:
            return self.fail('paramiko failed', stderr=failed[0]['stderr'])
        return self.ok(
            metrics={
                'commands': [item['command'] for item in results],
                'show_version': results[1]['stdout'],
            },
            reasons='ok',
            message='paramiko ok',
        )


CHECK_CLASS = Check
"""

PARAMIKO_TIMEOUT_CONTINUE_SCRIPT_TEXT = """# -*- coding: utf-8 -*-

from .common._base import BaseCheck


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'linux'
    PARAMIKO_AUTH_METHOD = 'password'

    def run(self):
        results = self._run_paramiko_commands([
            {
                'command': 'su -',
                'timeout': 0.05,
                'ignore_prompt': True,
            },
            {
                'command': 'whoami',
                'timeout': 0.05,
            },
        ])
        return self.ok(
            metrics={
                'commands': [item['command'] for item in results],
                'rcs': [item['rc'] for item in results],
                'timed_out_commands': [item['command'] for item in results if item.get('timed_out')],
                'whoami': results[1]['stdout'],
            },
            reasons='ok',
            message='paramiko continue ok',
        )


CHECK_CLASS = Check
"""

PARAMIKO_PROFILE_DICT_SCRIPT_TEXT = """# -*- coding: utf-8 -*-

from .common._base import BaseCheck


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = {
        'prompt_patterns': [r'NEVER_MATCHES'],
        'pager_patterns': [],
    }
    PARAMIKO_AUTH_METHOD = 'password'

    def run(self):
        results = self._run_paramiko_commands([
            'whoami',
        ])
        failed = [item for item in results if item['rc'] != 0]
        if failed:
            return self.fail('paramiko failed', stderr=failed[0]['stderr'])
        return self.ok(
            metrics={
                'commands': [item['command'] for item in results],
                'whoami': results[0]['stdout'],
            },
            reasons='ok',
            message='paramiko dict profile ok',
        )


CHECK_CLASS = Check
"""

PARAMIKO_HIDDEN_COMMAND_SCRIPT_TEXT = """# -*- coding: utf-8 -*-

from .common._base import BaseCheck


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'linux'
    PARAMIKO_AUTH_METHOD = 'password'

    def run(self):
        results = self._run_paramiko_commands([
            {
                'command': 'super-secret-password',
                'hide_command': True,
            },
        ])
        failed = [item for item in results if item['rc'] != 0]
        if failed:
            return self.fail('paramiko failed', stderr=failed[0]['stderr'])
        return self.ok(
            metrics={
                'display_command': results[0]['display_command'],
                'hide_command': results[0]['hide_command'],
            },
            reasons='ok',
            message='paramiko hidden ok',
        )


CHECK_CLASS = Check
"""


PARAMIKO_BECOME_SCRIPT_TEXT = """# -*- coding: utf-8 -*-

from .common._base import BaseCheck


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'linux'
    PARAMIKO_AUTH_METHOD = 'password'

    def run(self):
        results = self._run_paramiko_commands([
            'whoami',
            'id -un',
        ], become=True)
        failed = [item for item in results if item['rc'] != 0]
        if failed:
            return self.fail('paramiko become failed', stderr=failed[0]['stderr'])
        return self.ok(
            metrics={
                'commands': [item['command'] for item in results],
                'whoami': results[0]['stdout'],
                'id_un': results[1]['stdout'],
            },
            reasons='ok',
            message='paramiko become ok',
        )


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

    def create_paramiko_case_dir(self, root_dir, name='paramiko_case'):
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
                'inspection_code': 'N-TEST-PARAMIKO-01',
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
            {'channel': 'terminal', 'action': 'recv', 'stdout': 'terminal length 0\r\nRouter#'},
            {'channel': 'terminal', 'action': 'send', 'matcher_value': 'show version'},
            {'channel': 'terminal', 'action': 'recv', 'stdout': 'show version\r\nVendor OS\r\nRouter#'},
        ]

        with open(os.path.join(case_dir, 'case.json'), 'w', encoding='utf-8') as fh:
            json.dump(case_data, fh, ensure_ascii=False, indent=2)
            fh.write('\n')
        with open(os.path.join(case_dir, 'script.py'), 'w', encoding='utf-8') as fh:
            fh.write(PARAMIKO_SCRIPT_TEXT)
        with open(os.path.join(case_dir, 'replay.json'), 'w', encoding='utf-8') as fh:
            json.dump(replay_rules, fh, ensure_ascii=False, indent=2)
            fh.write('\n')

        return case_dir

    def create_paramiko_timeout_continue_case_dir(self, root_dir, name='paramiko_timeout_continue_case'):
        case_dir = os.path.join(root_dir, name)
        os.makedirs(case_dir, exist_ok=True)

        case_data = {
            'host': '127.0.0.1',
            'port': 22,
            'user': 'admin',
            'password': 'admin',
            'credentials': {
                'LINUX': [
                    {
                        'application_type_name': 'LINUX',
                        'credential_type_name': 'SSH',
                        'data': {
                            'username': 'admin',
                            'password': 'admin',
                        },
                    }
                ]
            },
            'thresholds': {},
            'item_sleep_sec': 0,
            'execution_id': 3,
            'host_id': 30,
            'job_id': 300,
            'item': {
                'inspection_code': 'L-TEST-PARAMIKO-TIMEOUT-01',
                'item_id': 90003,
                'application_type_name': 'LINUX',
                'threshold_list': [],
            },
        }
        replay_rules = [
            {'channel': 'terminal', 'action': 'recv', 'stdout': 'admin@linux:~$'},
            {'channel': 'terminal', 'action': 'send', 'matcher_value': 'su -'},
            {'channel': 'terminal', 'action': 'recv', 'stdout': 'su -\r\nPassword:'},
            {'channel': 'terminal', 'action': 'send', 'matcher_value': 'whoami'},
            {'channel': 'terminal', 'action': 'recv', 'stdout': 'whoami\r\nroot\r\nadmin@linux:~$'},
        ]

        with open(os.path.join(case_dir, 'case.json'), 'w', encoding='utf-8') as fh:
            json.dump(case_data, fh, ensure_ascii=False, indent=2)
            fh.write('\n')
        with open(os.path.join(case_dir, 'script.py'), 'w', encoding='utf-8') as fh:
            fh.write(PARAMIKO_TIMEOUT_CONTINUE_SCRIPT_TEXT)
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
            result = output['results'][0]
            self.assertEqual(result['status'], 'ok')
            self.assertEqual(result['metrics']['expected'], 'base')
            self.assertEqual(
                result['results'],
                [
                    {
                        'step': 1,
                        'command': 'echo hello',
                        'result': 'hello',
                    }
                ],
            )

            result_path = os.path.join(case_dir, 'result.json')
            self.assertTrue(os.path.isfile(result_path))
            with open(result_path, 'r', encoding='utf-8') as fh:
                saved_result = json.load(fh)
            self.assertEqual(
                saved_result['results'][0]['results'],
                result['results'],
            )

    def test_run_path_replay_ssh_become_matches_wrapped_command(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            case_dir = self.create_case_dir(tmp_dir, name='ssh_become_case')
            wrapped_cmd = "printf '%s\\n' 'root password' | sudo -S -p '' -u root -- sh -lc 'id -un'"

            with open(os.path.join(case_dir, 'case.json'), 'r', encoding='utf-8') as fh:
                case_data = json.load(fh)
            case_data['credentials']['LINUX'][0]['data'].update({
                'become_method': 'sudo',
                'become_user': 'root',
                'become_password': 'root password',
            })
            with open(os.path.join(case_dir, 'case.json'), 'w', encoding='utf-8') as fh:
                json.dump(case_data, fh, ensure_ascii=False, indent=2)
                fh.write('\n')
            with open(os.path.join(case_dir, 'script.py'), 'w', encoding='utf-8') as fh:
                fh.write(SSH_BECOME_SCRIPT_TEXT)
            with open(os.path.join(case_dir, 'replay.json'), 'w', encoding='utf-8') as fh:
                json.dump(
                    [
                        {
                            'matcher_type': 'exact',
                            'matcher_value': wrapped_cmd,
                            'rc': 0,
                            'stdout': 'root\n',
                            'stderr': '',
                        }
                    ],
                    fh,
                    ensure_ascii=False,
                    indent=2,
                )
                fh.write('\n')

            output, exit_code = replay_cli.run_path(case_dir, mode='replay')

            self.assertEqual(exit_code, 0)
            self.assertEqual(output['failed_items'], [])
            result = output['results'][0]
            self.assertEqual(result['status'], 'ok')
            self.assertEqual(result['metrics']['user'], 'root')
            self.assertEqual(result['message'], 'become ok')
            self.assertIn('raw_output', result)
            self.assertIn("sudo -S -p '' -u root -- sh -lc 'id -un'", result['raw_output'])
            self.assertNotIn('root password', result['raw_output'])

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
            with self.assertRaisesRegex(ValueError, 'single case directory'):
                replay_cli.run_path(tmp_dir, mode='live')

    def test_main_rejects_removed_override_file_argument(self):
        stderr = io.StringIO()
        with mock.patch('sys.stderr', stderr):
            with self.assertRaises(SystemExit) as exc:
                replay_cli.main(['--override-file', 'override.json', 'case_a'])

        self.assertEqual(exc.exception.code, 2)
        self.assertIn('unrecognized arguments: --override-file', stderr.getvalue())

    def test_run_path_replay_supports_paramiko_commands(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            case_dir = self.create_paramiko_case_dir(tmp_dir)

            output, exit_code = replay_cli.run_path(case_dir, mode='replay')

            self.assertEqual(exit_code, 0)
            self.assertEqual(output['failed_items'], [])
            self.assertEqual(output['results'][0]['status'], 'ok')
            self.assertEqual(
                output['results'][0]['metrics']['commands'],
                ['terminal length 0', 'show version'],
            )
            self.assertEqual(output['results'][0]['metrics']['show_version'], 'Vendor OS')

    def test_run_path_replay_paramiko_timeout_can_continue(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            case_dir = self.create_paramiko_timeout_continue_case_dir(tmp_dir)

            output, exit_code = replay_cli.run_path(case_dir, mode='replay')

            self.assertEqual(exit_code, 0)
            self.assertEqual(output['failed_items'], [])
            self.assertEqual(output['results'][0]['status'], 'ok')
            self.assertEqual(
                output['results'][0]['metrics']['commands'],
                ['su -', 'whoami'],
            )
            self.assertEqual(output['results'][0]['metrics']['rcs'], [124, 0])
            self.assertEqual(
                output['results'][0]['metrics']['timed_out_commands'],
                ['su -'],
            )
            self.assertEqual(output['results'][0]['metrics']['whoami'], 'root')

    def test_run_path_replay_paramiko_common_become_runs_before_actual_commands(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            case_dir = self.create_paramiko_timeout_continue_case_dir(tmp_dir, name='paramiko_become_case')

            with open(os.path.join(case_dir, 'case.json'), 'r', encoding='utf-8') as fh:
                case_data = json.load(fh)
            case_data['credentials']['LINUX'][0]['data'].update({
                'become': 'true',
                'become_method': 'su -',
                'become_user': 'root',
                'become_password': 'root-password',
            })
            with open(os.path.join(case_dir, 'case.json'), 'w', encoding='utf-8') as fh:
                json.dump(case_data, fh, ensure_ascii=False, indent=2)
                fh.write('\n')
            with open(os.path.join(case_dir, 'script.py'), 'w', encoding='utf-8') as fh:
                fh.write(PARAMIKO_BECOME_SCRIPT_TEXT)
            with open(os.path.join(case_dir, 'replay.json'), 'w', encoding='utf-8') as fh:
                json.dump(
                    [
                        {'channel': 'terminal', 'action': 'recv', 'stdout': 'admin@linux:~$'},
                        {'channel': 'terminal', 'action': 'send', 'matcher_value': 'su - root'},
                        {'channel': 'terminal', 'action': 'recv', 'stdout': 'su - root\r\nPassword:'},
                        {'channel': 'terminal', 'action': 'send', 'redacted': True},
                        {'channel': 'terminal', 'action': 'recv', 'stdout': '[root@linux ~]#'},
                        {'channel': 'terminal', 'action': 'send', 'matcher_value': 'id'},
                        {
                            'channel': 'terminal',
                            'action': 'recv',
                            'stdout': 'id\r\nuid=0(root) gid=0(root) groups=0(root)\r\n[root@linux ~]#',
                        },
                        {'channel': 'terminal', 'action': 'send', 'matcher_value': 'whoami'},
                        {'channel': 'terminal', 'action': 'recv', 'stdout': 'whoami\r\nroot\r\n[root@linux ~]#'},
                        {'channel': 'terminal', 'action': 'send', 'matcher_value': 'id -un'},
                        {'channel': 'terminal', 'action': 'recv', 'stdout': 'id -un\r\nroot\r\n[root@linux ~]#'},
                    ],
                    fh,
                    ensure_ascii=False,
                    indent=2,
                )
                fh.write('\n')

            output, exit_code = replay_cli.run_path(case_dir, mode='replay')

            self.assertEqual(exit_code, 0)
            self.assertEqual(output['failed_items'], [])
            self.assertEqual(output['results'][0]['status'], 'ok')
            self.assertEqual(output['results'][0]['metrics']['commands'], ['whoami', 'id -un'])
            self.assertEqual(output['results'][0]['metrics']['whoami'], 'root')
            self.assertEqual(output['results'][0]['metrics']['id_un'], 'root')
            self.assertNotIn('root-password', output['results'][0]['raw_output'])

    def test_paramiko_command_dict_validates_invalid_ignore_prompt(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            case_dir = self.create_paramiko_timeout_continue_case_dir(tmp_dir, name='paramiko_invalid_ignore_prompt')

            with open(os.path.join(case_dir, 'script.py'), 'w', encoding='utf-8') as fh:
                fh.write(
                    """# -*- coding: utf-8 -*-

from .common._base import BaseCheck


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'linux'
    PARAMIKO_AUTH_METHOD = 'password'

    def run(self):
        self._run_paramiko_commands([
            {
                'command': 'whoami',
                'ignore_prompt': 'maybe',
            },
        ])
        return self.ok(message='unreachable')


CHECK_CLASS = Check
"""
                )

            output, exit_code = replay_cli.run_path(case_dir, mode='replay')

            self.assertEqual(exit_code, 0)
            self.assertEqual(output['failed_items'], ['L-TEST-PARAMIKO-TIMEOUT-01'])
            self.assertEqual(output['results'][0]['status'], 'fail')
            self.assertEqual(output['results'][0]['error'], 'exec_error')
            self.assertIn('invalid paramiko ignore_prompt', output['results'][0]['message'])

    def test_paramiko_profile_dict_ignores_prompt_patterns(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            case_dir = self.create_paramiko_timeout_continue_case_dir(tmp_dir, name='paramiko_profile_dict_case')

            with open(os.path.join(case_dir, 'script.py'), 'w', encoding='utf-8') as fh:
                fh.write(PARAMIKO_PROFILE_DICT_SCRIPT_TEXT)
            with open(os.path.join(case_dir, 'replay.json'), 'w', encoding='utf-8') as fh:
                json.dump(
                    [
                        {'channel': 'terminal', 'action': 'recv', 'stdout': 'admin@linux:~$'},
                        {'channel': 'terminal', 'action': 'send', 'matcher_value': 'whoami'},
                        {'channel': 'terminal', 'action': 'recv', 'stdout': 'whoami\r\nadmin\r\nadmin@linux:~$'},
                    ],
                    fh,
                    ensure_ascii=False,
                    indent=2,
                )
                fh.write('\n')

            output, exit_code = replay_cli.run_path(case_dir, mode='replay')

            self.assertEqual(exit_code, 0)
            self.assertEqual(output['failed_items'], [])
            self.assertEqual(output['results'][0]['status'], 'ok')
            self.assertEqual(output['results'][0]['metrics']['commands'], ['whoami'])
            self.assertEqual(output['results'][0]['metrics']['whoami'], 'admin')

    def test_solaris_paramiko_profile_adds_legacy_algorithms(self):
        import paramiko

        check = BaseCheck({
            'host': '127.0.0.1',
            'port': 22,
            'user': 'admin',
            'password': 'admin',
        })
        options = check._paramiko_options()
        options['resolved_profile'] = check._resolve_paramiko_profile('solaris')

        kwargs = check._build_paramiko_connect_kwargs(options, 'password', paramiko)

        self.assertIn('transport_factory', kwargs)
        runner_kwargs = runner.build_paramiko_connect_kwargs(
            '127.0.0.1',
            22,
            'admin',
            'admin',
            {
                'profile': 'solaris',
                'timeout_sec': 10,
                'banner_timeout_sec': 10,
                'auth_timeout_sec': 10,
                'allow_agent': False,
                'look_for_keys': False,
            },
            'password',
            paramiko,
        )
        self.assertIn('transport_factory', runner_kwargs)
        left, right = socket.socketpair()
        transport = None
        try:
            transport = kwargs['transport_factory'](left)
            self.assertIn('diffie-hellman-group-exchange-sha1', transport._preferred_kex)
            self.assertIn('diffie-hellman-group14-sha1', transport._preferred_kex)
            self.assertIn('diffie-hellman-group1-sha1', transport._preferred_kex)
            self.assertIn('diffie-hellman-group-exchange-sha1', transport._kex_info)
            self.assertIn('diffie-hellman-group14-sha1', transport._kex_info)
            self.assertIn('diffie-hellman-group1-sha1', transport._kex_info)
            self.assertIn('ssh-rsa', transport._preferred_keys)
            self.assertIn('ssh-rsa', transport._key_info)
            self.assertIn('ssh-rsa', transport._key_info['ssh-rsa'].HASHES)
        finally:
            if transport is not None:
                try:
                    transport.close()
                except Exception:
                    pass
            right.close()

    def test_paramiko_command_dict_hides_command_in_raw_output(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            case_dir = self.create_paramiko_timeout_continue_case_dir(tmp_dir, name='paramiko_hidden_case')

            with open(os.path.join(case_dir, 'script.py'), 'w', encoding='utf-8') as fh:
                fh.write(PARAMIKO_HIDDEN_COMMAND_SCRIPT_TEXT)
            with open(os.path.join(case_dir, 'replay.json'), 'w', encoding='utf-8') as fh:
                json.dump(
                    [
                        {'channel': 'terminal', 'action': 'recv', 'stdout': 'admin@linux:~$'},
                        {'channel': 'terminal', 'action': 'send', 'matcher_value': 'super-secret-password'},
                        {'channel': 'terminal', 'action': 'recv', 'stdout': 'super-secret-password\r\nok\r\nadmin@linux:~$'},
                    ],
                    fh,
                    ensure_ascii=False,
                    indent=2,
                )
                fh.write('\n')

            output, exit_code = replay_cli.run_path(case_dir, mode='replay')

            self.assertEqual(exit_code, 0)
            self.assertEqual(output['failed_items'], [])
            self.assertEqual(output['results'][0]['status'], 'ok')
            self.assertEqual(output['results'][0]['metrics']['display_command'], '*******')
            self.assertTrue(output['results'][0]['metrics']['hide_command'])
            self.assertIn('실행 명령어: *******', output['results'][0]['raw_output'])
            self.assertNotIn('super-secret-password', output['results'][0]['raw_output'])
            self.assertEqual(output['results'][0]['results'][0]['command'], '*******')
            self.assertNotIn(
                'super-secret-password',
                json.dumps(output['results'][0]['results'], ensure_ascii=False),
            )


if __name__ == '__main__':
    unittest.main()
