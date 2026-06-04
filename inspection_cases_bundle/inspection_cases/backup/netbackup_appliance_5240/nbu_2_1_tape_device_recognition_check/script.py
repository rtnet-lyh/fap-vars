# -*- coding: utf-8 -*-

from .common._base import BaseCheck


COMMAND = 'tpconfig -l'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'    
    PARAMIKO_REUSE_SESSION = True
    PARAMIKO_COMMAND_TIMEOUT = 5 
    PARAMIKO_AUTH_TIMEOUT_SEC = 20

    def _allowed_statuses(self):
        raw = self.get_threshold_var('status_value', default='UP', value_type='str')
        return [item.strip() for item in str(raw or '').split(',') if item.strip()]

    def _run_command(self):
        try:
            self.get_elevate_for_aos()
        except Exception as exc:
            return None, self.fail('AOS 권한 상승 실패', message=str(exc))

        result = self._run_paramiko_commands(
            [{'command': COMMAND, 'timeout': 10}],
        )[0]
        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()
        if self._is_connection_error(result.get('rc'), stderr):
            return None, self.fail('호스트 연결 실패', message=stderr or 'Paramiko 연결 확인에 실패했습니다.', stderr=stderr)
        if result.get('rc') != 0:
            return None, self.fail('점검 명령 실행 실패', message='Tape 장치 구성 조회 명령 실행에 실패했습니다.', stdout=stdout, stderr=stderr)
        return stdout, None

    def _parse_drive_rows(self, stdout):
        has_robot = False
        rows = []
        for line in str(stdout or '').splitlines():
            parts = line.split()
            if not parts:
                continue
            if parts[0] == 'robot':
                has_robot = True
                continue
            if parts[0] == 'drive' and len(parts) >= 6:
                rows.append({
                    'drive_index': parts[2],
                    'drive_type': parts[3],
                    'drive_number': parts[4],
                    'status': parts[5],
                    'raw': line.strip(),
                })
        return has_robot, rows

    def run(self):
        stdout, error = self._run_command()
        if error:
            return error

        allowed_statuses = self._allowed_statuses()
        has_robot, rows = self._parse_drive_rows(stdout)
        thresholds = {'status_value': ','.join(allowed_statuses)}
        if not has_robot:
            return self.ok(metrics={'tape_configured': False, 'drive_count': 0}, thresholds=thresholds, reasons='robot 항목이 없어 Tape 미사용 장비로 판단했습니다.', message='Tape 장치 구성 미사용 상태')
        if not rows:
            return self.fail('tpconfig 출력 파싱 실패', message='robot 항목은 있으나 drive 상태 행을 찾지 못했습니다.', stdout=stdout, thresholds=thresholds)

        invalid_rows = [row for row in rows if row['status'] not in allowed_statuses]
        metrics = {
            'tape_configured': True,
            'drive_count': len(rows),
            'invalid_drive_count': len(invalid_rows),
            'invalid_drives': invalid_rows,
        }
        if invalid_rows:
            return self.fail(error='Tape drive Status 값이 기준과 다른 행이 있습니다.', metrics=metrics, thresholds=thresholds, reasons='Tape drive Status 값이 기준과 다른 행이 있습니다.', message='Tape 장치 인식 상태 경고: 비정상 drive %s개.' % len(invalid_rows))
        return self.ok(metrics=metrics, thresholds=thresholds, reasons='Tape drive Status 값이 기준을 만족합니다.', message='Tape 장치 인식 상태 점검 정상')


CHECK_CLASS = Check
