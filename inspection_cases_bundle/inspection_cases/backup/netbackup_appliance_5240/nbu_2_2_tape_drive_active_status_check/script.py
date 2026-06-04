# -*- coding: utf-8 -*-

from .common._base import BaseCheck


COMMAND = 'vmoprcmd -d ds'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'    
    PARAMIKO_REUSE_SESSION = True
    PARAMIKO_COMMAND_TIMEOUT = 5 
    PARAMIKO_AUTH_TIMEOUT_SEC = 20

    def _allowed_controls(self):
        raw = self.get_threshold_var('control_values', default='TLD,ACS,TLH,AVR', value_type='str')
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
            return None, self.fail('점검 명령 실행 실패', message='Tape drive 운용 상태 조회 명령 실행에 실패했습니다.', stdout=stdout, stderr=stderr)
        return stdout, None

    def _parse_drive_rows(self, stdout):
        if 'DRIVE STATUS' not in str(stdout or ''):
            return False, []
        rows = []
        for line in str(stdout or '').splitlines():
            parts = line.split()
            if not parts or not parts[0].isdigit() or len(parts) < 5:
                continue
            control = parts[2]
            control_value = control.split('-')[-1] if '-' in control else control
            rows.append({
                'drive': parts[0],
                'type': parts[1],
                'control': control,
                'control_value': control_value,
                'ready': parts[-3],
                'raw': line.strip(),
            })
        return True, rows

    def run(self):
        stdout, error = self._run_command()
        if error:
            return error

        allowed_controls = self._allowed_controls()
        has_status, rows = self._parse_drive_rows(stdout)
        thresholds = {'control_values': ','.join(allowed_controls), 'required_ready': 'Yes'}
        if not has_status:
            return self.ok(metrics={'tape_drive_status_present': False, 'drive_count': 0}, thresholds=thresholds, reasons='DRIVE STATUS 항목이 없어 Tape 미사용 장비로 판단했습니다.', message='Tape drive Active 상태 미사용')
        if not rows:
            return self.fail('vmoprcmd 출력 파싱 실패', message='DRIVE STATUS 출력에서 drive 행을 찾지 못했습니다.', stdout=stdout, thresholds=thresholds)

        invalid_rows = [row for row in rows if row['ready'] != 'Yes' or row['control_value'] not in allowed_controls]
        metrics = {
            'tape_drive_status_present': True,
            'drive_count': len(rows),
            'invalid_drive_count': len(invalid_rows),
            'invalid_drives': invalid_rows,
        }
        if invalid_rows:
            return self.fail(error='Ready 또는 Control 값이 기준을 만족하지 않는 drive가 있습니다.', metrics=metrics, thresholds=thresholds, reasons='Ready 또는 Control 값이 기준을 만족하지 않는 drive가 있습니다.', message='Tape drive Active 상태 경고: 비정상 drive %s개.' % len(invalid_rows))
        return self.ok(metrics=metrics, thresholds=thresholds, reasons='각 drive의 Ready 값과 Control 값이 기준을 만족합니다.', message='Tape drive Active 상태 점검 정상')


CHECK_CLASS = Check
