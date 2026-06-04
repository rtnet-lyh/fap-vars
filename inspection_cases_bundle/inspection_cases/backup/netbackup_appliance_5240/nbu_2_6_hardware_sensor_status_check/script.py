# -*- coding: utf-8 -*-

from .common._base import BaseCheck


COMMAND = 'ipmitool sdr elist all'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'    
    PARAMIKO_REUSE_SESSION = True
    PARAMIKO_COMMAND_TIMEOUT = 5 
    PARAMIKO_AUTH_TIMEOUT_SEC = 20  

    def _run_command(self):
        try:
            self.get_elevate_for_aos()
        except Exception as exc:
            return None, self.fail('AOS 권한 상승 실패', message=str(exc))

        result = self._run_paramiko_commands(
            [{'command': COMMAND, 'timeout': 10}]
        )[0]
        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()
        if self._is_connection_error(result.get('rc'), stderr):
            return None, self.fail('호스트 연결 실패', message=stderr or 'Paramiko 연결 확인에 실패했습니다.', stderr=stderr)
        if result.get('rc') != 0:
            return None, self.fail('점검 명령 실행 실패', message='하드웨어 센서 상태 조회 명령 실행에 실패했습니다.', stdout=stdout, stderr=stderr)
        return stdout, None

    def _parse_sensor_rows(self, stdout):
        rows = []
        for line in str(stdout or '').splitlines():
            if '|' not in line:
                continue
            parts = [part.strip() for part in line.split('|')]
            if len(parts) < 3:
                continue
            rows.append({
                'sensor': parts[0],
                'sensor_id': parts[1],
                'status': parts[2].lower(),
                'raw': line.strip(),
            })
        return rows

    def run(self):
        stdout, error = self._run_command()
        if error:
            return error

        rows = self._parse_sensor_rows(stdout)
        thresholds = {'allowed_statuses': ['ok', 'ns']}
        if not rows:
            return self.fail('ipmitool 출력 파싱 실패', message='ipmitool 출력에서 센서 상태 행을 찾지 못했습니다.', stdout=stdout, thresholds=thresholds)

        invalid_rows = [row for row in rows if row['status'] not in ('ok', 'ns')]
        metrics = {
            'sensor_count': len(rows),
            'invalid_sensor_count': len(invalid_rows),
            'invalid_sensors': invalid_rows,
        }
        if invalid_rows:
            return self.fail(error='센서 상태값이 ok/ns가 아닌 행이 있습니다.', metrics=metrics, thresholds=thresholds, reasons='센서 상태값이 ok/ns가 아닌 행이 있습니다.', message='하드웨어 센서 상태 경고: 비정상 센서 %s개.' % len(invalid_rows))
        return self.ok(metrics=metrics, thresholds=thresholds, reasons='모든 센서 상태값이 ok 또는 ns입니다.', message='하드웨어 센서 상태 점검 정상')


CHECK_CLASS = Check
