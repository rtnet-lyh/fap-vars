#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import unittest
from unittest import mock


CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

import runner


class FakeResponse:
    def __init__(self, std_out=b'', std_err=b'', status_code=0):
        self.std_out = std_out
        self.std_err = std_err
        self.status_code = status_code


class FakeSession:
    def __init__(self, response):
        self.response = response
        self.run_ps_calls = []
        self.run_cmd_calls = []

    def run_ps(self, command):
        self.run_ps_calls.append(command)
        return self.response

    def run_cmd(self, command):
        self.run_cmd_calls.append(command)
        return self.response


class FakeParamikoChannel:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


class FakeParamikoExecChannel:
    def __init__(self, status_code=0):
        self.status_code = status_code

    def recv_exit_status(self):
        return self.status_code


class FakeParamikoStream:
    def __init__(self, data=b'', status_code=0):
        self.data = data
        self.channel = FakeParamikoExecChannel(status_code)

    def read(self):
        return self.data


class FakeParamikoClient:
    def __init__(self, connect_error=None, exec_rc=0, exec_stdout=b'', exec_stderr=b''):
        self.connect_error = connect_error
        self.exec_rc = exec_rc
        self.exec_stdout = exec_stdout
        self.exec_stderr = exec_stderr
        self.connect_kwargs = None
        self.closed = False
        self.channel = FakeParamikoChannel()
        self.invoke_shell_calls = 0
        self.exec_commands = []

    def set_missing_host_key_policy(self, policy):
        self.policy = policy

    def connect(self, **kwargs):
        self.connect_kwargs = kwargs
        if self.connect_error:
            raise self.connect_error

    def invoke_shell(self):
        self.invoke_shell_calls += 1
        return self.channel

    def exec_command(self, command, timeout=None):
        self.exec_commands.append((command, timeout))
        return (
            FakeParamikoStream(),
            FakeParamikoStream(self.exec_stdout, self.exec_rc),
            FakeParamikoStream(self.exec_stderr),
        )

    def close(self):
        self.closed = True


SERVER_SSH_SCRIPT_TEXT = """# -*- coding: utf-8 -*-
from .common._base import BaseCheck


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def run(self):
        rc, out, err = self._ssh('actual-check')
        if rc != 0:
            return self.fail('actual failed', stderr=err)
        return self.ok(message='actual ok')


CHECK_CLASS = Check
"""


SERVER_PARAMIKO_SCRIPT_TEXT = """# -*- coding: utf-8 -*-
from .common._base import BaseCheck


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_AUTH_METHOD = 'password'

    def run(self):
        results = self._run_paramiko_commands(['actual-paramiko'])
        if not results or results[0].get('rc') != 0:
            return self.fail('actual paramiko failed')
        return self.ok(message='paramiko ok')


CHECK_CLASS = Check
"""


NETWORK_PARAMIKO_SCRIPT_TEXT = """# -*- coding: utf-8 -*-
from .common._base import BaseCheck


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_AUTH_METHOD = 'password'

    def run(self):
        return self.ok(message='network ok')


CHECK_CLASS = Check
"""


class RunnerWinrmTest(unittest.TestCase):
    def test_decode_stream_bytes_falls_back_to_cp949(self):
        raw = '한글 경로'.encode('cp949')
        self.assertEqual(runner.decode_stream_bytes(raw), '한글 경로')

    def test_run_winrm_powershell_prefixes_utf8_and_decodes_output(self):
        response = FakeResponse(std_out='한글 출력'.encode('cp949'), std_err=b'', status_code=0)
        session = FakeSession(response)

        with mock.patch.object(runner, '_winrm_session', return_value=session):
            rc, out, err = runner.run_winrm(
                'Write-Output test',
                'host',
                5985,
                'user',
                'password',
                '',
                {'shell': 'powershell'},
            )

        self.assertEqual(rc, 0)
        self.assertEqual(out, '한글 출력')
        self.assertEqual(err, '')
        self.assertEqual(len(session.run_ps_calls), 1)
        self.assertTrue(session.run_ps_calls[0].startswith(runner.POWERSHELL_UTF8_PREFIX))
        self.assertIn('Write-Output test', session.run_ps_calls[0])

    def test_run_winrm_cmd_does_not_prefix_powershell_encoding(self):
        response = FakeResponse(std_out=b'ok', std_err=b'', status_code=0)
        session = FakeSession(response)

        with mock.patch.object(runner, '_winrm_session', return_value=session):
            rc, out, err = runner.run_winrm(
                'dir',
                'host',
                5985,
                'user',
                'password',
                '',
                {'shell': 'cmd'},
            )

        self.assertEqual(rc, 0)
        self.assertEqual(out, 'ok')
        self.assertEqual(err, '')
        self.assertEqual(session.run_ps_calls, [])
        self.assertEqual(session.run_cmd_calls, ['dir'])

    def test_run_paramiko_precheck_password_auth(self):
        client = FakeParamikoClient()

        rc, out, err = runner.run_paramiko_precheck(
            '10.0.0.1',
            22,
            'admin',
            'secret',
            {'auth_method': 'password'},
            client_factory=lambda: client,
        )

        self.assertEqual((rc, out, err), (0, '', ''))
        self.assertEqual(client.connect_kwargs['password'], 'secret')
        self.assertNotIn('key_filename', client.connect_kwargs)

    def test_run_paramiko_precheck_key_auth_uses_default_public_key_path(self):
        client = FakeParamikoClient()

        rc, out, err = runner.run_paramiko_precheck(
            '10.0.0.1',
            22,
            'admin',
            '',
            {'auth_method': 'key'},
            client_factory=lambda: client,
        )

        self.assertEqual((rc, out, err), (0, '', ''))
        self.assertEqual(
            client.connect_kwargs['key_filename'],
            os.path.expanduser('~/.ssh/id_rsa.pub'),
        )
        self.assertNotIn('password', client.connect_kwargs)

    def test_run_paramiko_precheck_auto_falls_back_to_password(self):
        clients = [
            FakeParamikoClient(connect_error=RuntimeError('key rejected')),
            FakeParamikoClient(),
        ]

        def factory():
            return clients.pop(0)

        rc, out, err = runner.run_paramiko_precheck(
            '10.0.0.1',
            22,
            'admin',
            'secret',
            {'auth_method': 'auto'},
            client_factory=factory,
        )

        self.assertEqual((rc, out, err), (0, '', ''))


class RunnerBecomePrecheckTest(unittest.TestCase):
    def run_payload(self, payload, **kwargs):
        logger = mock.Mock()
        with mock.patch.object(runner, 'load_available_items', return_value=({}, set())):
            return runner.execute_runner(payload, logger=logger, **kwargs)

    def server_item(self, code, item_id, script_text=SERVER_SSH_SCRIPT_TEXT):
        return {
            'inspection_code': code,
            'item_id': item_id,
            'application_id': 100,
            'application_type_id': 10,
            'application_type_name': 'LINUX',
            'application_name': 'A',
            'application_family_name': 'A',
            'check_script': script_text,
        }

    def server_payload(self, items, app_data):
        return {
            'host': '10.0.0.1',
            'port': 22,
            'user': 'fallback',
            'password': 'fallback-password',
            'credentials': {
                'LINUX': [
                    {
                        'application_id': 100,
                        'application_type_id': 10,
                        'application_type_name': 'LINUX',
                        'credential_type_name': 'APPLICATION',
                        'data': app_data,
                    },
                    {
                        'application_id': 100,
                        'application_type_id': 10,
                        'application_type_name': 'LINUX',
                        'credential_type_name': 'SSH',
                        'data': {
                            'username': 'inspector',
                            'password': 'ssh-password',
                            'port': 22,
                        },
                    },
                ]
            },
            'items': items,
            'thresholds': {},
            'item_sleep_sec': 0,
        }

    def test_ssh_sudo_precheck_failure_blocks_related_items_once(self):
        calls = []

        def ssh_executor(cmd, host, port, user, password, ssh_options, timeout_sec=None):
            del host, port, user, password, ssh_options, timeout_sec
            calls.append(cmd)
            if cmd == 'true':
                return 0, '', ''
            if 'sudo -S' in cmd:
                return 1, '', 'Sorry, try again.'
            if cmd == 'actual-check':
                self.fail('actual check should not run after sudo precheck failure')
            return 0, '', ''

        payload = self.server_payload(
            [
                self.server_item('U-TEST-SUDO-01', 1),
                self.server_item('U-TEST-SUDO-01', 2),
            ],
            {
                'become': True,
                'become_method': 'sudo',
                'become_user': 'root',
                'become_password': 'bad-password',
            },
        )

        output = self.run_payload(payload, ssh_executor=ssh_executor)

        self.assertEqual(sum('sudo -S' in call for call in calls), 1)
        self.assertNotIn('actual-check', calls)
        self.assertEqual([res['status'] for res in output['results']], ['fail', 'fail'])
        self.assertEqual([res['error'] for res in output['results']], ['권한 상승 실패', '권한 상승 실패'])

    def test_paramiko_sudo_precheck_failure_blocks_paramiko_commands_once(self):
        clients = []

        def factory():
            client = FakeParamikoClient(exec_rc=1, exec_stderr=b'Sorry, try again.')
            clients.append(client)
            return client

        payload = self.server_payload(
            [self.server_item('U-TEST-PARAMIKO-SUDO-01', 1, SERVER_PARAMIKO_SCRIPT_TEXT)],
            {
                'become': True,
                'become_method': 'sudo',
                'become_user': 'root',
                'become_password': 'bad-password',
            },
        )

        output = self.run_payload(payload, paramiko_client_factory=factory)

        self.assertEqual(sum(len(client.exec_commands) for client in clients), 1)
        self.assertEqual(sum(client.invoke_shell_calls for client in clients), 1)
        self.assertIn('sudo -S', clients[-1].exec_commands[0][0])
        self.assertEqual(output['results'][0]['status'], 'fail')
        self.assertEqual(output['results'][0]['error'], '권한 상승 실패')

    def test_ssh_su_precheck_failure_uses_su_command_once(self):
        calls = []

        def ssh_executor(cmd, host, port, user, password, ssh_options, timeout_sec=None):
            del host, port, user, password, ssh_options, timeout_sec
            calls.append(cmd)
            if cmd == 'true':
                return 0, '', ''
            if 'su - root -c true' in cmd:
                return 1, '', 'Authentication failure'
            if cmd == 'actual-check':
                self.fail('actual check should not run after su precheck failure')
            return 0, '', ''

        payload = self.server_payload(
            [self.server_item('U-TEST-SU-01', 1)],
            {
                'become': 'true',
                'become_method': 'su',
                'become_user': 'root',
                'become_password': 'bad-password',
            },
        )

        output = self.run_payload(payload, ssh_executor=ssh_executor)

        self.assertEqual(sum('su - root -c true' in call for call in calls), 1)
        self.assertNotIn('actual-check', calls)
        self.assertEqual(output['results'][0]['status'], 'fail')
        self.assertEqual(output['results'][0]['error'], '권한 상승 실패')

    def test_become_false_ssh_item_skips_privilege_precheck(self):
        calls = []

        def ssh_executor(cmd, host, port, user, password, ssh_options, timeout_sec=None):
            del host, port, user, password, ssh_options, timeout_sec
            calls.append(cmd)
            if 'sudo -S' in cmd or 'su - root -c true' in cmd:
                self.fail('privilege precheck should not run when become is false')
            return 0, 'ok', ''

        payload = self.server_payload(
            [self.server_item('U-TEST-NO-BECOME-01', 1)],
            {
                'become': False,
                'become_method': 'sudo',
                'become_user': 'root',
                'become_password': 'bad-password',
            },
        )

        output = self.run_payload(payload, ssh_executor=ssh_executor)

        self.assertEqual(calls, ['true', 'actual-check'])
        self.assertEqual(output['results'][0]['status'], 'ok')

    def test_network_enable_paramiko_item_skips_privilege_precheck(self):
        clients = []

        def factory():
            client = FakeParamikoClient()
            clients.append(client)
            return client

        payload = {
            'host': '10.0.0.2',
            'port': 22,
            'user': 'admin',
            'password': 'admin',
            'credentials': {
                'NETWORK': [
                    {
                        'application_id': 200,
                        'application_type_id': 30,
                        'application_type_name': 'NETWORK',
                        'credential_type_name': 'NETWORK_DEVICE',
                        'data': {
                            'username': 'admin',
                            'password': 'admin',
                            'become': 'true',
                            'become_method': 'enable',
                            'become_password': 'enable-password',
                        },
                    }
                ]
            },
            'items': [
                {
                    'inspection_code': 'NETWORK-TEST-01',
                    'item_id': 1,
                    'application_id': 200,
                    'application_type_id': 30,
                    'application_type_name': 'NETWORK',
                    'application_name': 'CISCO_IOS',
                    'application_family_name': 'CISCO_IOS',
                    'check_script': NETWORK_PARAMIKO_SCRIPT_TEXT,
                }
            ],
            'thresholds': {},
            'item_sleep_sec': 0,
        }

        output = self.run_payload(payload, paramiko_client_factory=factory)

        self.assertEqual(sum(len(client.exec_commands) for client in clients), 0)
        self.assertEqual(sum(client.invoke_shell_calls for client in clients), 1)
        self.assertEqual(output['results'][0]['status'], 'ok')


if __name__ == '__main__':
    unittest.main()
