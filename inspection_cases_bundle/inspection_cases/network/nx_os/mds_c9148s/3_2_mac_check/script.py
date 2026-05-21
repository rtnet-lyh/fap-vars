# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


COMMAND = 'show arp'
ARP_RE = re.compile(r'^\S+\s+(?P<ip>\d+(?:\.\d+){3})\s+\S+\s+(?P<mac>[0-9a-f.]+)\s+\S+\s+(?P<interface>\S+)', re.IGNORECASE)


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def run(self):
        rc, out, err = self._ssh(COMMAND)
        if rc != 0:
            return self.fail('점검 명령 실행 실패', message=f'{COMMAND} 명령 실행에 실패했습니다.', stdout=(out or '').strip(), stderr=(err or '').strip())

        entries = [m.groupdict() for m in (ARP_RE.match(line.strip()) for line in (out or '').splitlines()) if m]
        metrics = {'arp_entry_count': len(entries), 'arp_entries': entries}
        if not entries:
            return self.fail('ARP 테이블 파싱 실패', message='Hardware Addr와 Interface가 있는 ARP 항목을 찾지 못했습니다.', stdout=(out or '').strip(), metrics=metrics)
        return self.ok(metrics=metrics, thresholds={}, reasons='Hardware Addr와 Interface가 있는 ARP 항목이 확인되었습니다.', message=f'ARP 테이블 점검이 정상 수행되었습니다. entries={len(entries)}.')


CHECK_CLASS = Check
