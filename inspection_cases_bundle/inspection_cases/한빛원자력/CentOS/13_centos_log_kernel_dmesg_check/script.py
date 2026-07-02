# -*- coding: utf-8 -*-

import re

from items.common._base import BaseCheck


CHECK_COMMAND = "dmesg | grep -i 'panic' || true"


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'


    def parse_output(self, output):
        lines = [line.strip() for line in (output or '').splitlines() if line.strip()]
        return {'log_lines': lines, 'log_line_count': len(lines)}

    def evaluate(self, metrics, fail_keywords, except_keywords):
        if metrics.get('failure_type'):
            return 'fail'
        fail_items = [item.strip().lower() for item in re.split(r'[|,\n]+', fail_keywords or '') if item.strip()]
        except_items = [item.strip().lower() for item in re.split(r'[|,\n]+', except_keywords or '') if item.strip()]
        matched = []
        for line in metrics['log_lines']:
            lowered = line.lower()
            if any(keyword in lowered for keyword in except_items):
                continue
            for keyword in fail_items:
                if keyword in lowered:
                    matched.append({'keyword': keyword, 'line': line})
                    break
        metrics['matched_fail_count'] = len(matched)
        metrics['matched_fail_logs'] = matched
        return 'fail' if matched else 'ok'

    def build_result(self, metrics, fail_keywords, except_keywords, status):
        criteria = '제외 키워드 필터링 후 장애 키워드가 포함된 로그가 없어야 함'
        if metrics.get('failure_type'):
            return {'message': '로그 키워드 점검 실패', 'results': metrics.get('reason', ''), 'criteria': criteria}
        results = '로그 행 수=%d, 장애 키워드 매칭 수=%d' % (metrics['log_line_count'], metrics.get('matched_fail_count', 0))
        message = '로그 키워드 점검 양호' if status == 'ok' else '장애 키워드가 포함된 로그가 발견되었습니다.'
        return {'message': message, 'results': results, 'criteria': criteria}

    def run(self):
        fail_keywords = self.get_threshold_var('fail_keywords', default='', value_type='str')
        except_keywords = self.get_threshold_var('except_keywords', default='', value_type='str')

        rc, output, error = self._ssh(CHECK_COMMAND)

        if rc != 0:
            metrics = {
                'failure_type': 'command_failure',
                'rc': rc,
                'reason': (error or output or '명령 실행에 실패했습니다.').strip(),
            }
        else:
            metrics = self.parse_output(output)

        status = self.evaluate(metrics, fail_keywords, except_keywords)
        result = self.build_result(metrics, fail_keywords, except_keywords, status)

        return self.result(
            status=status,
            message=result['message'],
            metrics=metrics,
            results=result['results'],
            criteria=result['criteria'],
        )


CHECK_CLASS = Check