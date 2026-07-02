# -*- coding: utf-8 -*-

import re

from items.common._base import BaseCheck


CHECK_COMMAND = 'df -i'
# ---------------------------------------------------------------------
# threshold 변수 가이드
# max_inode_percent = 80.0
# ---------------------------------------------------------------------

class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'


    def parse_output(self, output):
        entries = []
        for line in (output or '').splitlines():
            parts = line.split()
            if len(parts) < 6 or not parts[4].endswith('%') or parts[0].lower() == 'filesystem':
                continue
            try:
                entries.append({'filesystem': parts[0], 'inode_use_percent': int(parts[4].rstrip('%')), 'mount_point': parts[5]})
            except Exception:
                return {'failure_type': 'parse_failure', 'reason': 'IUse% 값이 숫자가 아닙니다.'}
        if not entries:
            return {'failure_type': 'parse_failure', 'reason': 'df -i 출력에서 파일시스템 행을 찾을 수 없습니다.'}
        return {'filesystems': entries, 'max_inode_percent': max(item['inode_use_percent'] for item in entries)}

    def evaluate(self, metrics, max_inode_percent):
        if metrics.get('failure_type'):
            return 'fail'
        return 'fail' if metrics['max_inode_percent'] > max_inode_percent else 'ok'

    def build_result(self, metrics, max_inode_percent, status):
        criteria = f"""모든 파일시스템 IUse% <= {max_inode_percent:.1f}%
            실패: 명령 실패, 파싱 실패 또는 기준 초과"""
        if metrics.get('failure_type'):
            return {'message': 'inode 사용률 점검 실패', 'results': metrics.get('reason', ''), 'criteria': criteria}
        offenders = [item for item in metrics['filesystems'] if item['inode_use_percent'] > max_inode_percent]
        results = '파일시스템 수=%d, 최대 inode 사용률=%.1f%%' % (len(metrics['filesystems']), metrics['max_inode_percent'])
        message = 'inode 사용률 점검 양호' if status == 'ok' else 'inode 사용률이 기준을 초과했습니다: ' + ', '.join('%s=%s%%' % (item['mount_point'], item['inode_use_percent']) for item in offenders)
        return {'message': message, 'results': results, 'criteria': criteria}

    def run(self):
        max_inode_percent = self.get_threshold_var('max_inode_percent', default=80.0, value_type='float')

        rc, output, error = self._ssh(CHECK_COMMAND)

        if rc != 0:
            metrics = {
                'failure_type': 'command_failure',
                'rc': rc,
                'reason': (error or output or '명령 실행에 실패했습니다.').strip(),
            }
        else:
            metrics = self.parse_output(output)

        status = self.evaluate(metrics, max_inode_percent)
        result = self.build_result(metrics, max_inode_percent, status)

        return self.result(
            status=status,
            message=result['message'],
            metrics=metrics,
            results=result['results'],
            criteria=result['criteria'],
        )


CHECK_CLASS = Check