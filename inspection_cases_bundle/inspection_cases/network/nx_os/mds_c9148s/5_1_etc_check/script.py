# -*- coding: utf-8 -*-

from .common._base import BaseCheck


COMMAND = 'show environment'
BAD_STATUSES = {'fail', 'failed', 'faulty', 'warning', 'critical', 'major', 'minor', 'down', 'unknown'}


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'
    SSH_CONTROL_MASTER = False

    def run(self):
        rc, out, err = self._ssh(COMMAND)
        if rc != 0:
            return self.fail('점검 명령 실행 실패', message=f'{COMMAND} 명령 실행에 실패했습니다.', stdout=(out or '').strip(), stderr=(err or '').strip())

        lines = [line.strip() for line in (out or '').splitlines() if line.strip()]
        if not lines:
            return self.fail('환경 상태 파싱 실패', message='show environment 출력이 비어 있습니다.', stdout=(out or '').strip())

        bad = [line for line in lines if line.split()[-1].lower() in BAD_STATUSES]
        metrics = {'abnormal_status_count': len(bad), 'abnormal_status_lines': bad}
        if bad:
            return self.warn(metrics=metrics, thresholds={'abnormal_statuses': sorted(BAD_STATUSES)}, reasons='환경 상태에서 비정상 status가 탐지되었습니다.', message=f'환경 상태 비정상 항목 {len(bad)}건.')
        return self.ok(metrics=metrics, thresholds={'abnormal_statuses': sorted(BAD_STATUSES)}, reasons='환경 상태에서 비정상 status가 탐지되지 않았습니다.', message='환경 상태 점검이 정상 수행되었습니다.')


CHECK_CLASS = Check
