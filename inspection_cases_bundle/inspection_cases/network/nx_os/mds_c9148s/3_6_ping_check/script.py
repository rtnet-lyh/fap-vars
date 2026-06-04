# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


COUNT = 5
STATS_RE = re.compile(r'(\d+) packets transmitted,\s*(\d+) received.*?([0-9.]+)% packet loss')


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'
    SSH_CONTROL_MASTER = False

    def run(self):
        ping_ip = str(self.get_threshold_var('ping_ip', default='193.1.0.207', value_type='str')).strip()
        thresholds = {'ping_ip': ping_ip, 'ping_count': COUNT}
        if not ping_ip:
            return self.fail('임계치 미정의', message='ping_ip 값이 필요합니다.', thresholds=thresholds)

        command = f'ping {ping_ip} count {COUNT}'
        rc, out, err = self._ssh(command)
        if rc != 0:
            return self.fail('점검 명령 실행 실패', message=f'{command} 명령 실행에 실패했습니다.', stdout=(out or '').strip(), stderr=(err or '').strip(), thresholds=thresholds)

        match = STATS_RE.search(out or '')
        if not match:
            return self.fail('ping 결과 파싱 실패', message='ping statistics를 해석하지 못했습니다.', stdout=(out or '').strip(), thresholds=thresholds)

        sent, received, loss = int(match.group(1)), int(match.group(2)), float(match.group(3))
        metrics = {'packets_transmitted': sent, 'packets_received': received, 'packet_loss_percent': loss}
        if received != COUNT:
            return self.warn(metrics=metrics, thresholds=thresholds, reasons=f'{COUNT} received 조건을 만족하지 못했습니다.', message=f'ping 수신 패킷 부족: received={received}.')
        return self.ok(metrics=metrics, thresholds=thresholds, reasons=f'{COUNT} received 조건을 만족했습니다.', message='통신 테스트가 정상 수행되었습니다.')


CHECK_CLASS = Check
