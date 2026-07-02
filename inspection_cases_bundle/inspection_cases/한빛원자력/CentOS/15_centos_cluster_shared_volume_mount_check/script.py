# -*- coding: utf-8 -*-

import re

from items.common._base import BaseCheck


CHECK_COMMAND = 'mount'
# ---------------------------------------------------------------------
# threshold 변수 가이드
# shared_volume_required = False
# shared_volume_types = nfs, nfs4, cifs, gfs2, ocfs2
# mount_option_required = rw
# ---------------------------------------------------------------------

class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'


    def parse_output(self, output):
        mounts = []
        for line in (output or '').splitlines():
            match = re.match(r'^(\S+)\s+on\s+(\S+)\s+type\s+(\S+)\s+\(([^)]*)\)', line.strip())
            if match:
                mounts.append({'source': match.group(1), 'mount_point': match.group(2), 'type': match.group(3), 'options': match.group(4).split(',')})
        if not mounts:
            return {'failure_type': 'parse_failure', 'reason': 'mount 출력에서 파싱 가능한 행을 찾을 수 없습니다.'}
        return {'mounts': mounts, 'mount_count': len(mounts)}

    def evaluate(self, metrics, shared_volume_required, shared_volume_types, mount_option_required):
        if metrics.get('failure_type'):
            return 'fail'
        types = [item.strip() for item in re.split(r'[|,\n]+', shared_volume_types or '') if item.strip()]
        shared = [item for item in metrics['mounts'] if item['type'] in types]
        metrics['shared_mounts'] = shared
        if not shared:
            return 'fail' if shared_volume_required else 'excluded'
        bad = [item for item in shared if mount_option_required and mount_option_required not in item['options']]
        metrics['policy_violations'] = bad
        return 'fail' if bad else 'ok'

    def build_result(self, metrics, shared_volume_required, shared_volume_types, mount_option_required, status):
        criteria = '공유 볼륨 타입이 %s 중 하나이고 마운트 옵션에 %s 포함' % (shared_volume_types, mount_option_required)
        if metrics.get('failure_type'):
            return {'message': '공유 볼륨 점검 실패', 'results': metrics.get('reason', ''), 'criteria': criteria}
        results = '마운트 수=%d, 공유 볼륨 마운트 수=%d' % (metrics['mount_count'], len(metrics.get('shared_mounts', [])))
        if status == 'excluded':
            message = '공유 볼륨 점검 대상이 아닙니다.'
        else:
            message = '공유 볼륨 점검 양호' if status == 'ok' else '공유 볼륨 상태가 기준을 만족하지 않습니다.'
        return {'message': message, 'results': results, 'criteria': criteria}

    def run(self):
        shared_volume_required = self.get_threshold_var('shared_volume_required', default=False, value_type='bool')
        shared_volume_types = self.get_threshold_var('shared_volume_types', default='nfs|nfs4|cifs|gfs2|ocfs2', value_type='str')
        mount_option_required = self.get_threshold_var('mount_option_required', default='rw', value_type='str')

        rc, output, error = self._ssh(CHECK_COMMAND)

        if rc != 0:
            metrics = {
                'failure_type': 'command_failure',
                'rc': rc,
                'reason': (error or output or '명령 실행에 실패했습니다.').strip(),
            }
        else:
            metrics = self.parse_output(output)

        status = self.evaluate(metrics, shared_volume_required, shared_volume_types, mount_option_required)
        result = self.build_result(metrics, shared_volume_required, shared_volume_types, mount_option_required, status)

        return self.result(
            status=status,
            message=result['message'],
            metrics=metrics,
            results=result['results'],
            criteria=result['criteria'],
        )


CHECK_CLASS = Check