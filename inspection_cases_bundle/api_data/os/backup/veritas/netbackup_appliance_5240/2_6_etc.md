# type_name

일상점검

# area_name

backup

# category_name

상태점검

# application_type

veritas

# application

netbackup_appliance_5240

# inspection_code


BK-NBU5240-008

# is_required

필수

# inspection_name

장비 기타 물리장치 점검

# inspection_content

Power Supply 이중화 상태, FAN 등 상태 점검

# inspection_command

```bash
ipmitool sdr elist all
```

# inspection_output

```text
netbackup:/home/maintenance # ipmitool sdr elist all
System Airflow   | 11h | ok  | 23.1 | 41 CFM
BB Lft Rear Temp | 14h | ok  |  7.1 | 34 degrees C
Riser 3 Temp     | 17h | ok  | 16.3 | 37 degrees C
BB P1 VR Temp    | 20h | ok  |  7.1 | 44 degrees C
Front Panel Temp | 21h | ok  | 12.1 | 16 degrees C
SSB Temp         | 22h | ok  |  7.1 | 55 degrees C
BB P2 VR Temp    | 23h | ok  |  7.2 | 41 degrees C
BB BMC Temp      | 24h | ok  |  7.1 | 43 degrees C
BB Rt Rear Temp  | 25h | ok  |  7.1 | 42 degrees C
OCP Mod Temp     | 26h | ok  | 44.1 | 38 degrees C
Riser 1 Temp     | 27h | ok  | 16.1 | 41 degrees C
HSBP 1 Temp      | 29h | ok  | 15.1 | 34 degrees C
Riser 2 Temp     | 2Ch | ok  | 16.2 | 32 degrees C
SAS Mod Temp     | 2Dh | ok  | 44.1 | 42 degrees C
Exit Air Temp    | 2Eh | ok  |  7.1 | 54 degrees C
System Fan 1     | 30h | ok  | 29.1 | 5618 RPM
```

# description

- 명령어: 장비의 Sensor Data Record 정보를 조회하여 하드웨어 상태를 확인하는 명령어.
- 컬럼 값: 센서명|센서ID|상태값|인스턴스번호|상태 설명

- **양호**: 상태값 컬럼 내 값이 'ok','ns'인 경우.
- **경고**: 상태값 컬럼 내 값이 'ok','ns'이 아닌 경우.
- **확인 필요**: 명령어 실패 및 파싱 불가.

# thresholds

[]

# inspection_script

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
