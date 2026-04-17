# -*- coding: utf-8 -*-

import re


class NetworkHelper(object):
    def __init__(self, check):
        self.check = check

    def _normalize_variant(self, variant=None):
        if variant:
            text = str(variant).strip().lower().replace('-', '_')
            return text

        payload = self.check.ctx.get('item_payload') or {}
        for key in ('os_family', 'application_version', 'application_version_name'):
            value = payload.get(key)
            if value not in (None, ''):
                text = str(value).strip().lower().replace('-', '_')
                if text:
                    return text
        return 'ios'

    def run_show(self, cmd):
        rc, out, err = self.check._ssh(cmd)
        if rc != 0:
            return rc, out or '', (err or '').strip()
        return rc, out or '', ''

    def run_config(self, variant=None):
        return self.run_show('show running-config')

    def section_vty(self, variant=None):
        normalized = self._normalize_variant(variant)
        commands = ['show running-config | section line vty']
        if normalized in ('nx_os', 'nxos'):
            commands.append('show running-config | sec line vty')

        last_rc, last_out, last_err = 1, '', ''
        for cmd in commands:
            rc, out, err = self.run_show(cmd)
            last_rc, last_out, last_err = rc, out, err
            if rc == 0 or (out or '').strip():
                return rc, out, err
        return last_rc, last_out, last_err

    def grep_lines(self, text, pattern):
        return [
            line.strip()
            for line in (text or '').splitlines()
            if re.search(pattern, line, re.IGNORECASE)
        ]

    def has(self, text, pattern):
        return re.search(pattern, text or '', re.IGNORECASE | re.MULTILINE) is not None
