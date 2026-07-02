# -*- coding: utf-8 -*-

import re

from items.common._base import BaseCheck


CHECK_COMMAND = 'multipath -ll'
# ---------------------------------------------------------------------
# threshold 변수 가이드
# required_multipath_device: 운영 기준 장치
# min_path_count: 2
# multipath_path_state: active ready running
# ---------------------------------------------------------------------

class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_AUTH_TIMEOUT_SEC = 30

    def parse_output(self, output):
        text = output or ''
        if not text.strip():
            return {'not_applicable': True, 'reason': 'multipath 장치를 찾을 수 없어 점검 대상에서 제외합니다.'}
        devices = len(re.findall(r'\bdm-\d+\b', text))
        path_lines = []
        for line in text.splitlines():
            if re.search(r'\b(active|enabled)\b\s+\bready\b\s+\brunning\b', line):
                path_lines.append(line.strip())
        if not devices:
            return {'failure_type': 'parse_failure', 'reason': 'multipath 출력에서 장치 헤더를 찾을 수 없습니다.'}
        return {'multipath_device_count': devices, 'path_count': len(path_lines), 'path_lines': path_lines}

    def evaluate(self, metrics, required_multipath_device, min_path_count, multipath_path_state):
        if metrics.get('not_applicable'):
            return 'excluded'
        if metrics.get('failure_type'):
            return 'fail'
        if metrics['path_count'] < min_path_count:
            return 'fail'
        return 'ok'

    def build_result(self, metrics, required_multipath_device, min_path_count, multipath_path_state, status):
        criteria = 'multipath 경로 수 >= %d 및 경로 상태가 %s와 일치' % (min_path_count, multipath_path_state)
        if metrics.get('not_applicable'):
            return {'message': 'multipath 점검 대상이 아닙니다.', 'results': metrics.get('reason', ''), 'criteria': criteria}
        if metrics.get('failure_type'):
            return {'message': 'multipath 점검 실패', 'results': metrics.get('reason', ''), 'criteria': criteria}
        results = 'multipath 장치 수=%d, 경로 수=%d' % (metrics['multipath_device_count'], metrics['path_count'])
        message = 'multipath 점검 양호' if status == 'ok' else 'multipath 상태가 기준을 만족하지 않습니다.'
        return {'message': message, 'results': results, 'criteria': criteria}

    def run(self):
        required_multipath_device = self.get_threshold_var('required_multipath_device', default='', value_type='str')
        min_path_count = self.get_threshold_var('min_path_count', default=2, value_type='int')
        multipath_path_state = self.get_threshold_var('multipath_path_state', default='active ready running', value_type='str')

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

        status = self.evaluate(metrics, required_multipath_device, min_path_count, multipath_path_state)
        result = self.build_result(metrics, required_multipath_device, min_path_count, multipath_path_state, status)

        return self.result(
            status=status,
            message=result['message'],
            metrics=metrics,
            results=result['results'],
            criteria=result['criteria'],
        )


CHECK_CLASS = Check