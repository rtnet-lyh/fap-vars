# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


COMMAND = 'show ip route'
GATEWAY_RE = re.compile(r'Default gateway is\s+(\d+(?:\.\d+){3})')


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'
    SSH_CONTROL_MASTER = False

    def run(self):
        expected = str(self.get_threshold_var('gateway_ip', default='193.1.0.254', value_type='str')).strip()
        thresholds = {'gateway_ip': expected}
        if not expected:
            return self.fail('임계치 미정의', message='gateway_ip 값이 필요합니다.', thresholds=thresholds)

        rc, out, err = self._ssh(COMMAND)
        if rc != 0:
            return self.fail('점검 명령 실행 실패', message=f'{COMMAND} 명령 실행에 실패했습니다.', stdout=(out or '').strip(), stderr=(err or '').strip(), thresholds=thresholds)

        match = GATEWAY_RE.search(out or '')
        if not match:
            return self.fail('라우팅 테이블 파싱 실패', message='Default gateway 값을 찾지 못했습니다.', stdout=(out or '').strip(), thresholds=thresholds)

        actual = match.group(1)
        metrics = {'default_gateway': actual}
        if actual != expected:
            return self.warn(metrics=metrics, thresholds=thresholds, reasons=f'Default gateway {actual}가 기준 {expected}와 다릅니다.', message='Default gateway 기준 불일치')
        return self.ok(metrics=metrics, thresholds=thresholds, reasons='Default gateway가 기준값과 일치합니다.', message='라우팅 테이블 점검이 정상 수행되었습니다.')


CHECK_CLASS = Check
