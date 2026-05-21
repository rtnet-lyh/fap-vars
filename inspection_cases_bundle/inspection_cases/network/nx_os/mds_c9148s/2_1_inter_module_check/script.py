# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


COMMAND = 'show interface brief'
ROW_RE = re.compile(r'^(fc\S+)\s+\S+\s+\S+\s+\S+\s+(\S+)')


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def _split(self, value):
        return [item for item in re.split(r'[\s,]+', str(value or '').strip()) if item]

    def run(self):
        expected = self._split(self.get_threshold_var('up_interface', default='', value_type='str'))
        thresholds = {'up_interface': expected}
        if not expected:
            return self.fail('임계치 미정의', message='up_interface 값이 필요합니다.', thresholds=thresholds)

        rc, out, err = self._ssh(COMMAND)
        if rc != 0:
            return self.fail('점검 명령 실행 실패', message=f'{COMMAND} 명령 실행에 실패했습니다.', stdout=(out or '').strip(), stderr=(err or '').strip(), thresholds=thresholds)

        statuses = {m.group(1): m.group(2) for m in (ROW_RE.match(line.strip()) for line in (out or '').splitlines()) if m}
        if not statuses:
            return self.fail('인터페이스 상태 파싱 실패', message='show interface brief 결과를 해석하지 못했습니다.', stdout=(out or '').strip(), thresholds=thresholds)

        bad = [{'interface': name, 'status': statuses.get(name, 'missing')} for name in expected if statuses.get(name) != 'up']
        metrics = {'checked_interface_count': len(expected), 'bad_interfaces': bad, 'interface_statuses': statuses}
        if bad:
            return self.warn(metrics=metrics, thresholds=thresholds, reasons=f'{len(bad)}개 운영대상 인터페이스가 up 상태가 아닙니다.', message='운영대상 인터페이스 상태 기준 미달')
        return self.ok(metrics=metrics, thresholds=thresholds, reasons='운영대상 인터페이스가 모두 up 상태입니다.', message='인터페이스 상태 점검이 정상 수행되었습니다.')


CHECK_CLASS = Check
