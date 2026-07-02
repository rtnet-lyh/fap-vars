# -*- coding: utf-8 -*-

import re

from items.common._base import BaseCheck


CHECK_COMMAND = 'cat /proc/partitions'
# ---------------------------------------------------------------------
# threshold 변수 가이드
# expected_disk_inventory = 
# unexpected_missing_device_allowed = false
# ---------------------------------------------------------------------

class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'


    def parse_output(self, output):
        devices = []
        for line in (output or '').splitlines():
            parts = line.split()
            if len(parts) == 4 and parts[0].isdigit() and parts[1].isdigit() and parts[2].isdigit():
                devices.append(parts[3])
        if not devices:
            return {'failure_type': 'parse_failure', 'reason': '/proc/partitions에서 디스크 장치 행을 찾을 수 없습니다.'}
        return {'device_count': len(devices), 'devices': devices}

    def evaluate(self, metrics, expected_disk_inventory, unexpected_missing_device_allowed):
        if metrics.get('failure_type'):
            return 'fail'
        expected = [item.strip() for item in re.split(r'[|,\n]+', expected_disk_inventory or '') if item.strip()]
        if not expected:
            return 'ok'
        missing = [item for item in expected if item not in metrics['devices']]
        metrics['missing_devices'] = missing
        return 'ok' if not missing or unexpected_missing_device_allowed else 'fail'

    def build_result(self, metrics, expected_disk_inventory, unexpected_missing_device_allowed, status):
        criteria = '디스크 목록을 읽을 수 있고 설정된 기대 장치가 모두 존재해야 함'
        if metrics.get('failure_type'):
            return {'message': '디스크 인식 점검 실패', 'results': metrics.get('reason', ''), 'criteria': criteria}
        results = '디스크 장치 수=%d' % metrics['device_count']
        message = '디스크 인식 점검 양호' if status == 'ok' else '디스크 인식 상태가 기준을 만족하지 않습니다.'
        return {'message': message, 'results': results, 'criteria': criteria}

    def run(self):
        expected_disk_inventory = self.get_threshold_var('expected_disk_inventory', default='', value_type='str')
        unexpected_missing_device_allowed = self.get_threshold_var('unexpected_missing_device_allowed', default=False, value_type='bool')

        rc, output, error = self._ssh(CHECK_COMMAND)

        if rc != 0:
            metrics = {
                'failure_type': 'command_failure',
                'rc': rc,
                'reason': (error or output or '명령 실행에 실패했습니다.').strip(),
            }
        else:
            metrics = self.parse_output(output)

        status = self.evaluate(metrics, expected_disk_inventory, unexpected_missing_device_allowed)
        result = self.build_result(metrics, expected_disk_inventory, unexpected_missing_device_allowed, status)

        return self.result(
            status=status,
            message=result['message'],
            metrics=metrics,
            results=result['results'],
            criteria=result['criteria'],
        )


CHECK_CLASS = Check