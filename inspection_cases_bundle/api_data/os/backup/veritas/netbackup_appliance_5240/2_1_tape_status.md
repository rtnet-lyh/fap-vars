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

BACKUP-VERITAS-NBU5240-REPLAY-003

# is_required

필수

# inspection_name

장비 Tape 관리 장치 인식 점검

# inspection_content

드라이브, 라이브러리 인식 상태 점검

# inspection_command

```bash
tpconfig -l
```

# inspection_output

```text

```

# description

- 명령어: NetBackup에서 구성된 Tape, Drive, Device 정보를 확인하는 명령어. 
- 출력 결과에 'robot' 항목 존재 시 tape이 구성되어있다고 판단.
- Tape 미 사용 장비(출력 결과: 결과없음)에는 '해당 없음','양호' 처리가 옳아보임.

[참고]
- 'Device Path'가 긴 경우 터미널 화면에서 줄바꿈이 발생되어 정렬이 깨질 수 있으므로 파싱 시 고정 컬럼위치만으로 판단하지 않도록 주의 필요.
- AI: 'Status'에 나올 수 있는 값이 'UP', 'DOWN', 'DISABLED', '-'라고 함.

- **양호**: 'robot' 값이 존재하지 않거나,'robot' 값이 존재하면서 'status' 값이 `status_value`인 경우.
- **경고**: 'robot' 값이 존재하고, 'status' 값이 `status_value`가 아닌 경우.
- **확인 필요**: 명령어 실패 및 파싱 불가.

# thresholds

[
    {id: null, key: "status_value", value: "UP", sortOrder: 0}
]

# inspection_script

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
