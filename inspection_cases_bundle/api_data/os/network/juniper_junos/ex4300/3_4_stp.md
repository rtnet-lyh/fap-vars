# type_name

일상점검

# area_name

network

# category_name

상태점검

# application_type

juniper_junos

# application

ex4300

# inspection_code


NW-JUN-EX4300-009

# is_required

권고

# inspection_name

STP 상태 점검

# inspection_content

STP 설정을 통해 Loop 구조를 방지하고 원활한 통신상태를 확인

# inspection_command

```bash
show spannig-tree
```

# inspection_output

```text
falcon@Center_Server_J4300_B> show spanning-tree interface

Spanning tree interface parameters for instance 0

Interface                  Port ID    Designated         Designated         Port    State  Role
                                       port ID           bridge ID          Cost
ge-0/0/28                  128:490      128:490   8192.c8fe6a91c080        20000    FWD    DESG
ge-0/0/29                  128:491      128:491   8192.c8fe6a91c080        20000    FWD    DESG
xe-0/0/35                  128:492      128:494   4096.f4bfa8edae40         2000    FWD    ROOT
```

# description

- 명령어: 장비의 STP 인터페이스별 상태를 확인하는 명령어.
- State: STP 포트의 현재 전달 상태를 의미.
    - FWD: Forwarding 상태로, 트래픽을 정상 전달하는 상태.
    - BLK, DSC: Loop 방지를 위해 트래픽 전달을 차단하는 상태.

- Role: STP에서 해당 포트가 수행하는 역할을 의미.
    - ROOT: Root Bridge 방향으로 선택된 Root port를 의미.
    - DESG: Designated port로, 해당 세그먼트에서 트래픽을 전달하는 정상포트
    - ALT: Root Port 장애 시 대체 경로, 평상시에는 Loop 방지를 위해 차단 상태 일 수 있음.

[정상 State/Role 조합]
State  Role     설명
FWD     DESG     Designated 정상 전달 포트
FWD     ROOT     Root Bridge 방향 정상 전달 포트
BLK     ALT      Loop 방지를 위해 차단된 대체 포트
DSC     ALT      Loop 방지를 위해 차단된 대체 포트

[참고]
AI를 통해 수집한 정상 조합임. 실제와 다를 수 있음

- **양호**: 정상 State/Role 조합인 경우.
- **경고**: 정상 State/Role 조합이 아닌 경우.
- **확인 필요**: 명령어 실패 및 파싱 불가

# thresholds

[]

# inspection_script

# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


COMMAND_ERROR_MARKERS = ('syntax error', 'unknown command', 'invalid command', 'unknown keyword', 'missing argument')
COMMAND = 'show spanning-tree interface'
VALID_STP_COMBINATIONS = {('FWD', 'DESG'), ('FWD', 'ROOT'), ('BLK', 'ALT'), ('DSC', 'ALT')}


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'generic_network'
    PARAMIKO_REUSE_SESSION = True

    def _run_command(self, command):
        results = self._run_paramiko_commands([command], profile=self.PARAMIKO_PROFILE)
        if not results:
            return None, self.fail('점검 명령 실행 실패', message='Paramiko 명령 실행 결과가 비어 있습니다.')
        result = results[0]
        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()
        if result.get('rc') != 0:
            return None, self.fail('점검 명령 실행 실패', message=f'{command} 명령 실행에 실패했습니다.', stdout=stdout, stderr=stderr)
        error_text = self._detect_cli_error(stdout, stderr)
        if error_text:
            return None, self.fail('점검 명령 실행 실패', message=f'{command} 명령 출력에서 오류가 확인되었습니다: {error_text}', stdout=stdout, stderr=stderr)
        return stdout, None

    def _detect_cli_error(self, *texts):
        for text in texts:
            for line in str(text or '').splitlines():
                stripped = line.strip()
                lowered = stripped.lower()
                if stripped and any(marker in lowered for marker in COMMAND_ERROR_MARKERS):
                    return stripped
        return ''

    def _parse_stp_rows(self, text):
        rows = []
        for line in (text or '').splitlines():
            parts = line.split()
            if len(parts) >= 7 and re.match(r'^[a-z]+-\d+/\d+/\d+$', parts[0], re.IGNORECASE):
                rows.append({'interface': parts[0], 'state': parts[-2].upper(), 'role': parts[-1].upper()})
        return rows

    def run(self):
        stdout, error = self._run_command(COMMAND)
        if error:
            return error

        rows = self._parse_stp_rows(stdout)
        if not rows:
            return self.fail('STP 파싱 실패', message='show spanning-tree interface 출력에서 STP 행을 찾지 못했습니다.', stdout=stdout, thresholds={})
        invalid = [row for row in rows if (row['state'], row['role']) not in VALID_STP_COMBINATIONS]
        metrics = {'stp_interface_count': len(rows), 'invalid_stp_interfaces': invalid, 'stp_interfaces': rows}
        if invalid:
            return self.fail('STP 상태 기준 미달', message=f'정상 State/Role 조합이 아닌 인터페이스가 {len(invalid)}개 있습니다.', stdout=stdout, metrics=metrics, thresholds={})
        return self.ok(metrics=metrics, thresholds={}, reasons='모든 STP State/Role 조합이 정상 범위입니다.', message='STP 상태 점검 정상.')


CHECK_CLASS = Check
