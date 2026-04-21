#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import unittest


CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from terminal import TerminalSession


class FakeTransport:
    def __init__(self, chunks):
        self.chunks = list(chunks)
        self.sent = []
        self.closed = False

    def send(self, text, newline=False, redacted=False):
        self.sent.append({
            'text': text,
            'newline': newline,
            'redacted': redacted,
        })

    def read_chunk(self, timeout_sec=None):
        del timeout_sec
        if self.closed:
            return ''
        if not self.chunks:
            self.closed = True
            return ''
        return self.chunks.pop(0)

    def close(self):
        self.closed = True


class NoDataTransport(FakeTransport):
    def __init__(self):
        super().__init__([])

    def read_chunk(self, timeout_sec=None):
        del timeout_sec
        return None


class TerminalSessionTest(unittest.TestCase):
    def test_run_strips_command_echo_and_prompt(self):
        transport = FakeTransport(['show run\r\nCurrent configuration : 123\r\nRouter#'])
        session = TerminalSession(transport)
        session._started = True

        output = session.run('show run', [r'Router#'])

        self.assertEqual(output, 'Current configuration : 123')
        self.assertEqual(
            transport.sent,
            [{'text': 'show run', 'newline': True, 'redacted': False}],
        )

    def test_expect_auto_responds_to_pager(self):
        transport = FakeTransport(['line1\n--More--', '\nline2\nRouter#'])
        history = []
        session = TerminalSession(
            transport,
            history_callback=history.append,
            pager_patterns=[r'--More--'],
            pager_response=' ',
        )

        result = session.expect([r'Router#'])

        self.assertTrue(result.matched)
        self.assertFalse(result.timed_out)
        self.assertEqual(result.body.strip(), 'line1\n\nline2')
        self.assertEqual(
            transport.sent,
            [{'text': ' ', 'newline': False, 'redacted': False}],
        )
        self.assertEqual(history[0]['kind'], 'send')
        self.assertTrue(history[0]['auto'])
        self.assertEqual(history[1]['kind'], 'recv')

    def test_expect_timeout_returns_unmatched_result_and_clears_buffer(self):
        transport = NoDataTransport()
        history = []
        session = TerminalSession(
            transport,
            history_callback=history.append,
            default_timeout_sec=0.01,
        )
        session.buffer = 'partial output'

        result = session.expect([r'Router#'])

        self.assertFalse(result.matched)
        self.assertTrue(result.timed_out)
        self.assertEqual(result.index, -1)
        self.assertEqual(result.text, 'partial output')
        self.assertEqual(session.buffer, '')
        self.assertEqual(history[0]['kind'], 'recv')
        self.assertTrue(history[0]['timeout'])

    def test_expect_strict_timeout_raises_and_preserves_buffer(self):
        transport = NoDataTransport()
        session = TerminalSession(transport, default_timeout_sec=0.01)
        session.buffer = 'partial output'

        with self.assertRaises(TimeoutError):
            session.expect([r'Router#'], strict=True)

        self.assertEqual(session.buffer, 'partial output')

    def test_drain_collects_output_without_patterns(self):
        transport = FakeTransport(['line1\n', 'line2\n'])
        history = []
        session = TerminalSession(transport, history_callback=history.append)

        output = session.drain(timeout_sec=0.01)

        self.assertEqual(output, 'line1\nline2\n')
        self.assertEqual(session.buffer, '')
        self.assertEqual(history[0]['kind'], 'recv')
        self.assertTrue(history[0]['drain'])

    def test_normalizes_osc_title_escape_sequences(self):
        transport = FakeTransport(['\x1b]0;fap@localhost:~\x07[fap@localhost ~]$'])
        session = TerminalSession(transport)

        result = session.expect([r'\$\s*$'])

        self.assertEqual(result.text, '[fap@localhost ~]$')

    def test_first_sendline_drains_initial_output(self):
        transport = FakeTransport(['login banner\nRouter>'])
        history = []
        session = TerminalSession(transport, history_callback=history.append)

        session.sendline('show version')

        self.assertEqual(
            transport.sent,
            [{'text': 'show version', 'newline': True, 'redacted': False}],
        )
        self.assertEqual(history[0]['kind'], 'recv')
        self.assertTrue(history[0]['drain'])
        self.assertEqual(history[0]['text'], 'login banner\nRouter>')
        self.assertEqual(history[1]['kind'], 'send')

    def test_sendline_records_redacted_history(self):
        transport = FakeTransport(['Password:'])
        history = []
        session = TerminalSession(transport, history_callback=history.append)
        session._started = True

        session.sendline('secret', redact=True)

        self.assertEqual(
            transport.sent,
            [{'text': 'secret', 'newline': True, 'redacted': True}],
        )
        self.assertEqual(history[0]['text'], '*****')
        self.assertTrue(history[0]['redacted'])

    def test_run_command_uses_cisco_profile_prompt(self):
        transport = FakeTransport(['show version\nCisco IOS Software\nRouter#'])
        session = TerminalSession(transport)
        session._started = True
        session.use_profile('cisco_ios')

        result = session.run_command('show version', timeout_sec=5)

        self.assertTrue(result.matched)
        self.assertEqual(result.output, 'Cisco IOS Software')
        self.assertEqual(
            transport.sent,
            [{'text': 'show version', 'newline': True, 'redacted': False}],
        )

    def test_enter_privilege_handles_enable_password_flow(self):
        transport = FakeTransport(['Router>', 'Password:', 'Router#'])
        session = TerminalSession(transport)
        session.use_profile('cisco_ios')

        changed = session.enter_privilege(password='secret')

        self.assertTrue(changed)
        self.assertEqual(
            transport.sent,
            [
                {'text': 'enable', 'newline': True, 'redacted': False},
                {'text': 'secret', 'newline': True, 'redacted': True},
            ],
        )

    def test_run_command_uses_junos_profile_prompt(self):
        transport = FakeTransport(['show version\nJunos OS 20.4\nuser@router>'])
        session = TerminalSession(transport)
        session._started = True
        session.use_profile('junos')

        result = session.run_command('show version', timeout_sec=5)

        self.assertTrue(result.matched)
        self.assertEqual(result.output, 'Junos OS 20.4')

    def test_run_command_accepts_generic_profile_override(self):
        transport = FakeTransport(['display version\nVendor OS\nswitch]'])
        session = TerminalSession(transport)
        session._started = True
        session.use_profile({
            'prompt_patterns': [r'(?:^|\n)[^\n\r]+\]\s*$'],
            'pager_patterns': [r'Press any key'],
            'pager_response': ' ',
        })

        result = session.run_command('display version', timeout_sec=5)

        self.assertTrue(result.matched)
        self.assertEqual(result.output, 'Vendor OS')

    def test_run_until_marker_returns_output_before_marker(self):
        transport = FakeTransport(['echo hi; printf "\\n__END__\\n"\nhi\n__END__\n'])
        session = TerminalSession(transport)
        session._started = True

        result = session.run_until_marker('echo hi', marker='__END__', timeout_sec=5)

        self.assertTrue(result.matched)
        self.assertEqual(result.output, 'hi')

    def test_run_su_command_collects_multiline_output(self):
        transport = FakeTransport(['Password:', 'line1\nline2\n__END__\n'])
        session = TerminalSession(transport)
        session._started = True

        result = session.run_su_command(
            'cat /etc/passwd',
            password='secret',
            marker='__END__',
            timeout_sec=5,
        )

        self.assertTrue(result.matched)
        self.assertEqual(result.output, 'line1\nline2')
        self.assertEqual(transport.sent[1], {'text': 'secret', 'newline': True, 'redacted': True})


if __name__ == '__main__':
    unittest.main()
