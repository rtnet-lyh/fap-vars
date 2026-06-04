# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


COMMAND = 'show system resources'
MEMORY_RE = re.compile(r'Memory usage:\s*(\d+)K total,\s*(\d+)K used,\s*(\d+)K free')
STATUS_RE = re.compile(r'Current memory status:\s*(\S+)', re.IGNORECASE)


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'
    SSH_CONTROL_MASTER = False
    
    def run(self):
        max_usage = self.get_threshold_var('max_mem_usage_percent', default=90.0, value_type='float')
        thresholds = {'max_mem_usage_percent': max_usage}
        rc, out, err = self._ssh(COMMAND)
        if rc != 0:
            return self.fail('점검 명령 실행 실패', message=f'{COMMAND} 명령 실행에 실패했습니다.', stdout=(out or '').strip(), stderr=(err or '').strip(), thresholds=thresholds)

        text = (out or '').strip()
        memory = MEMORY_RE.search(text)
        status = STATUS_RE.search(text)
        if not memory or not status:
            return self.fail('메모리 사용률 파싱 실패', message='Memory usage 또는 Current memory status 값을 해석하지 못했습니다.', stdout=text, thresholds=thresholds)

        total_kb, used_kb, free_kb = [int(memory.group(i)) for i in (1, 2, 3)]
        usage = round(used_kb / total_kb * 100, 2) if total_kb else 0.0
        metrics = {
            'memory_total_kb': total_kb,
            'memory_used_kb': used_kb,
            'memory_free_kb': free_kb,
            'memory_usage_percent': usage,
            'current_memory_status': status.group(1),
        }
        if status.group(1).upper() != 'OK':
            return self.warn(metrics=metrics, thresholds=thresholds, reasons='Current memory status가 OK가 아닙니다.', message=f'Current memory status={status.group(1)}')
        if usage > max_usage:
            return self.warn(metrics=metrics, thresholds=thresholds, reasons=f'메모리 사용률 {usage}%가 임계치 {max_usage}%를 초과했습니다.', message=f'메모리 사용률 기준 초과: {usage}%')
        return self.ok(metrics=metrics, thresholds=thresholds, reasons=f'메모리 사용률 {usage}%가 임계치 {max_usage}% 이하입니다.', message=f'메모리 사용률 점검이 정상 수행되었습니다. usage={usage}%.')


CHECK_CLASS = Check
