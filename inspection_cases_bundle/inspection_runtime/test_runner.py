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


class FakeParamikoClient:
    def __init__(self, connect_error=None):
        self.connect_error = connect_error
        self.connect_kwargs = None
        self.closed = False
        self.channel = FakeParamikoChannel()

    def set_missing_host_key_policy(self, policy):
        self.policy = policy

    def connect(self, **kwargs):
        self.connect_kwargs = kwargs
        if self.connect_error:
            raise self.connect_error

    def invoke_shell(self):
        return self.channel

    def close(self):
        self.closed = True


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


if __name__ == '__main__':
    unittest.main()
