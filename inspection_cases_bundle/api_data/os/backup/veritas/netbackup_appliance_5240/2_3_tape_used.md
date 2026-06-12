# type_name

일상점검

# area_name

상태점검

# category_name

backup

# application_type

veritas

# application

netbackup_appliance_5240

# inspection_code

BACKUP-VERITAS-NBU5240-REPLAY-005

# is_required

필수

# inspection_name

Tape 정상 점검

# inspection_content

테이프 미디어 불량 상태 점검 및 사용상태 점검

# inspection_command

```bash
bpmedialist -mlist -U
```

# inspection_output

```text

```

# description

- 명령어: Tape Media 정보를 확인하는 명령어.
- '<------- STATUS ------->' 컬럼은 Tape Media 사용 상태를 나타낸다.


[참고]
- '<------- STATUS ------->' 컬럼 내 어떤 문구가 올 수 있는지 확인 불가
- AI: 'FROZEN', 'SUSPENDED', 'UNAVAIL' 값은 경고라고 함.

- **양호**: 명령어 결과가 존재하지 않거나, 각 라인마다 STATUS 값이 `media_status_value`인 경우.
- **경고**: 명령어 결과가 존재하지 않거나, 각 라인마다 STATUS 값이 `media_status_value`이 아닌 경우.
- **확인 필요**: 명령어 실패 및 파싱 불가.

# thresholds

[
    {id: null, key: "media_status_value", value: "FULL,__EMPTY__", sortOrder: 0}
]

# inspection_script

# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


COMMAND = 'bpmedialist -mlist -U'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'    
    PARAMIKO_REUSE_SESSION = True
    PARAMIKO_COMMAND_TIMEOUT = 5 
    PARAMIKO_AUTH_TIMEOUT_SEC = 20

    def _allowed_statuses(self):
        raw = self.get_threshold_var('media_status_value', default='FULL,__EMPTY__', value_type='str')
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
            return None, self.fail('점검 명령 실행 실패', message='Tape media 상태 조회 명령 실행에 실패했습니다.', stdout=stdout, stderr=stderr)
        return stdout, None

    def _parse_media_rows(self, stdout):
        rows = []
        current = None
        for line in str(stdout or '').splitlines():
            parts = line.split()
            if not parts:
                continue
            if re.match(r'^[A-Z0-9]{3,}$', parts[0]) and len(parts) >= 2 and parts[1].isdigit():
                current = {'media_id': parts[0], 'status': '__EMPTY__', 'raw': line.strip()}
                rows.append(current)
                continue
            if not current or len(parts) < 3 or not parts[0].isdigit():
                continue
            if 'N/A' in parts:
                na_idx = parts.index('N/A')
                if na_idx + 1 < len(parts):
                    current['status'] = parts[na_idx + 1]
        return rows

    def run(self):
        stdout, error = self._run_command()
        if error:
            return error

        allowed_statuses = self._allowed_statuses()
        rows = self._parse_media_rows(stdout)
        thresholds = {'media_status_value': ','.join(allowed_statuses)}
        if not rows:
            return self.ok(metrics={'media_count': 0, 'invalid_media_count': 0}, thresholds=thresholds, reasons='Tape media 출력 행이 없어 Tape 미사용 장비로 판단했습니다.', message='Tape media 상태 미사용')

        invalid_rows = [row for row in rows if row['status'] not in allowed_statuses]
        metrics = {
            'media_count': len(rows),
            'invalid_media_count': len(invalid_rows),
            'invalid_media': invalid_rows,
            'media_statuses': rows,
        }
        if invalid_rows:
            return self.fail(error='Tape media STATUS 값이 기준을 만족하지 않는 행이 있습니다.', metrics=metrics, thresholds=thresholds, reasons='Tape media STATUS 값이 기준을 만족하지 않는 행이 있습니다.', message='Tape media 상태 경고: 비정상 media %s개.' % len(invalid_rows))
        return self.ok(metrics=metrics, thresholds=thresholds, reasons='Tape media STATUS 값이 기준을 만족합니다.', message='Tape media 상태 점검 정상')


CHECK_CLASS = Check
