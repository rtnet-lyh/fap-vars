# -*- coding: utf-8 -*-

import re

from items.common._base import BaseCheck


CHECK_COMMAND = 'dmidecode -t memory'
# ---------------------------------------------------------------------
# threshold 변수 가이드
# memory_device_required_fields: Size, Type, Locator
# ---------------------------------------------------------------------

class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_AUTH_TIMEOUT_SEC = 30


    def parse_output(self, output):
        blocks = re.split(r'\n\s*Memory Device\s*\n', '\n' + (output or ''))
        devices = []
        for block in blocks[1:]:
            item = {}
            for line in block.splitlines():
                if ':' in line:
                    key, value = line.split(':', 1)
                    item[key.strip()] = value.strip()
            if item:
                devices.append(item)
        if not devices:
            return {'failure_type': 'parse_failure', 'reason': 'dmidecode 출력에서 Memory Device 블록을 찾을 수 없습니다.'}
        return {'memory_device_count': len(devices), 'devices': devices}

    def evaluate(self, metrics, memory_device_required_fields):
        if metrics.get('failure_type'):
            return 'fail'
        required = [item.strip() for item in re.split(r'[|,\n]+', memory_device_required_fields or '') if item.strip()]
        bad = []
        for device in metrics['devices']:
            missing = [field for field in required if not device.get(field) or device.get(field) == 'No Module Installed']
            if missing:
                bad.append({'locator': device.get('Locator', ''), 'missing': missing})
        metrics['bad_devices'] = bad
        return 'fail' if bad else 'ok'

    def build_result(self, metrics, memory_device_required_fields, status):
        criteria = '모든 메모리 장치에 필수 필드가 존재해야 함: %s' % memory_device_required_fields
        if metrics.get('failure_type'):
            return {'message': '메모리 인식 점검 실패', 'results': metrics.get('reason', ''), 'criteria': criteria}
        results = '메모리 장치 수=%d, 기준 미달 장치 수=%d' % (metrics['memory_device_count'], len(metrics.get('bad_devices', [])))
        message = '메모리 인식 점검 양호' if status == 'ok' else '메모리 인식 상태가 기준을 만족하지 않습니다.'
        return {'message': message, 'results': results, 'criteria': criteria}

    def run(self):
        memory_device_required_fields = self.get_threshold_var(
            'memory_device_required_fields',
            default='Size|Type|Locator',
            value_type='str',
        )
    
        results = self._run_paramiko_commands(CHECK_COMMAND, become=True)
        last = results[-1] if results else {}
    
        rc = last.get('rc', 1)
        output = last.get('stdout', '')
        error = last.get('stderr', '')
    
        if rc != 0:
            metrics = {
                'failure_type': 'command_failure',
                'rc': rc,
                'reason': (error or output or '명령 실행에 실패했습니다.').strip(),
            }
        else:
            metrics = self.parse_output(output)
    
        status = self.evaluate(metrics, memory_device_required_fields)
        result = self.build_result(metrics, memory_device_required_fields, status)
    
        return self.result(
            status=status,
            message=result['message'],
            metrics=metrics,
            results=result['results'],
            criteria=result['criteria'],
        )


CHECK_CLASS = Check