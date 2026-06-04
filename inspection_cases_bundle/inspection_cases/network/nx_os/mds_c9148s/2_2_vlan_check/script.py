# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


COMMAND = 'show vsan'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'
    SSH_CONTROL_MASTER = False
    
    def _split(self, value):
        return [item for item in re.split(r'[\s,]+', str(value or '').strip()) if item]

    def _parse(self, text):
        vsans = {}
        current = None
        for line in (text or '').splitlines():
            info = re.search(r'^vsan\s+(\d+)\s+information', line.strip(), re.IGNORECASE)
            state = re.search(r'name:\S+\s+state:(\S+)', line.strip(), re.IGNORECASE)
            if info:
                current = info.group(1)
                vsans[current] = {}
            elif current and state:
                vsans[current]['state'] = state.group(1)
        return vsans

    def run(self):
        expected = self._split(self.get_threshold_var('active_vsan', default='10', value_type='str'))
        thresholds = {'active_vsan': expected}
        if not expected:
            return self.fail('임계치 미정의', message='active_vsan 값이 필요합니다.', thresholds=thresholds)

        rc, out, err = self._ssh(COMMAND)
        if rc != 0:
            return self.fail('점검 명령 실행 실패', message=f'{COMMAND} 명령 실행에 실패했습니다.', stdout=(out or '').strip(), stderr=(err or '').strip(), thresholds=thresholds)

        vsans = self._parse(out)
        if not vsans:
            return self.fail('VSAN 상태 파싱 실패', message='show vsan 결과를 해석하지 못했습니다.', stdout=(out or '').strip(), thresholds=thresholds)

        bad = [{'vsan': name, 'state': vsans.get(name, {}).get('state', 'missing')} for name in expected if vsans.get(name, {}).get('state') != 'active']
        metrics = {'checked_vsan_count': len(expected), 'bad_vsans': bad, 'vsans': vsans}
        if bad:
            return self.warn(metrics=metrics, thresholds=thresholds, reasons=f'{len(bad)}개 운영대상 VSAN이 active 상태가 아닙니다.', message='운영대상 VSAN 상태 기준 미달')
        return self.ok(metrics=metrics, thresholds=thresholds, reasons='운영대상 VSAN이 모두 active 상태입니다.', message='VSAN 상태 점검이 정상 수행되었습니다.')


CHECK_CLASS = Check
