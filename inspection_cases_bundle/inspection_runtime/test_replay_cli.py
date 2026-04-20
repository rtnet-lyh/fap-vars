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


if __name__ == '__main__':
    unittest.main()
