# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


COMMAND = 'show logging | include {include_keyword}'
PROMPT_RE = re.compile(r'^[A-Za-z0-9_.:/-]+[>#]\s*$')


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'
    SSH_CONTROL_MASTER = False

    def _lines(self, text):
        lines = []
        for line in (text or '').splitlines():
            stripped = line.strip()
            if not stripped or PROMPT_RE.match(stripped) or stripped.endswith('# ' + COMMAND):
                continue
            lines.append(stripped)
        return lines

    def run(self):
        include_keyword = self.get_threshold_var(key='include_keyword', default='fail|error|warning|stop|down', value_type='str')
        command = COMMAND.format(include_keyword=include_keyword)
        rc, out, err = self._ssh(command)
        if rc != 0:
            return self.fail('점검 명령 실행 실패', message=f'{command} 명령 실행에 실패했습니다.', stdout=(out or '').strip(), stderr=(err or '').strip())

        lines = self._lines(out)
        metrics = {'matched_log_count': len(lines), 'matched_logs': lines}
        if lines:
            return self.warn(metrics=metrics, thresholds={'include_keyword': include_keyword}, reasons='fail/error/warning/stop/down 관련 로그가 출력되었습니다.', message=f'시스템 로그 키워드 출력 {len(lines)}건.')
        return self.ok(metrics=metrics, thresholds={'include_keyword': include_keyword}, reasons='fail/error/warning/stop/down 관련 로그가 출력되지 않았습니다.', message='시스템 로그 점검이 정상 수행되었습니다.')


CHECK_CLASS = Check
