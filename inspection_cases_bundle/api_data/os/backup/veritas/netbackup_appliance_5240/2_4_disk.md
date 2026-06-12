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

BACKUP-VERITAS-NBU5240-REPLAY-006

# is_required

필수

# inspection_name

디스크 상태 점검

# inspection_content

디스크 Fault 상태 점검

# inspection_command

```bash
/opt/MegaRAID/storcli/storcli64 /c0 /eall /sall show
```

# inspection_output

```text
tggitsbackup:/home/maintenance # /opt/MegaRAID/storcli/storcli64 /c0 /eall /sall show
CLI Version = 007.1704.0000.0000 Jan 16, 2021
Operating system = Linux 4.18.0-372.105.1.el8_6.x86_64
Controller = 0
Status = Success
Description = Show Drive Information Succeeded.


Drive Information :
=================

------------------------------------------------------------------------------
EID:Slt DID State DG       Size Intf Med SED PI SeSz Model            Sp Type
------------------------------------------------------------------------------
252:0    11 Onln   0 930.390 GB SAS  HDD N   N  512B ST1000NM0045     U  -
252:1    10 Onln   0 930.390 GB SAS  HDD N   N  512B ST1000NM0045     U  -
252:2    16 Onln   0 930.390 GB SAS  HDD N   N  512B ST1000NM0045     U  -
252:3    12 Onln   0 930.390 GB SAS  HDD N   N  512B ST1000NM0045     U  -
252:4    15 Onln   0 930.390 GB SAS  HDD N   N  512B ST1000NM0045     U  -
252:5    14 Onln   0 930.390 GB SAS  HDD N   N  512B ST1000NM0045     U  -
252:6     8 Onln   0 930.390 GB SAS  HDD N   N  512B ST1000NM0045     U  -
252:7    13 DHS    0 930.390 GB SAS  HDD N   N  512B ST1000NM0045     D  -
------------------------------------------------------------------------------

EID=Enclosure Device ID|Slt=Slot No|DID=Device ID|DG=DriveGroup
DHS=Dedicated Hot Spare|UGood=Unconfigured Good|GHS=Global Hotspare
UBad=Unconfigured Bad|Sntze=Sanitize|Onln=Online|Offln=Offline|Intf=Interface
Med=Media Type|SED=Self Encryptive Drive|PI=Protection Info
SeSz=Sector Size|Sp=Spun|U=Up|D=Down|T=Transition|F=Foreign
UGUnsp=UGood Unsupported|UGShld=UGood shielded|HSPShld=Hotspare shielded
CFShld=Configured shielded|Cpybck=CopyBack|CBShld=Copyback Shielded
UBUnsp=UBad Unsupported|Rbld=Rebuild
```

# description

- 명령어: RAID 컨트롤러에 연결된 전체 물리 디스크 상태를 확인하는 명령어.
- '/c0' 옵션은 0번 RAID 컨트롤러를 의미함.

[참고]
- AI: 'State' 컬럼 설명
Onln: 온라인 상태(양호)
DHS: 대기상태(양호)
offln, failed, UBad: 장애 또는 비정상(경고)

- **양호**: 각 라인마다 State 값이 `disk_state_value`인 경우.
- **경고**: 각 라인마다 State 값이 `disk_state_value`이 아닌 경우.
- **확인 필요**: 명령어 실패 및 파싱 불가.

# thresholds

[
    {id: null, key: "disk_state_value", value: "Onln,DHS", sortOrder: 0}
]

# inspection_script

# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


COMMAND = '/opt/MegaRAID/storcli/storcli64 /c0 /eall /sall show'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'    
    PARAMIKO_REUSE_SESSION = True
    PARAMIKO_COMMAND_TIMEOUT = 5 
    PARAMIKO_AUTH_TIMEOUT_SEC = 20    

    def _allowed_states(self):
        raw = self.get_threshold_var('disk_state_value', default='Onln,DHS', value_type='str')
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
            return None, self.fail('점검 명령 실행 실패', message='물리 디스크 상태 조회 명령 실행에 실패했습니다.', stdout=stdout, stderr=stderr)
        return stdout, None

    def _parse_disk_rows(self, stdout):
        rows = []
        for line in str(stdout or '').splitlines():
            parts = line.split()
            if len(parts) < 3 or not re.match(r'^\d+:\d+$', parts[0]):
                continue
            rows.append({
                'eid_slot': parts[0],
                'did': parts[1],
                'state': parts[2],
                'raw': line.strip(),
            })
        return rows

    def run(self):
        stdout, error = self._run_command()
        if error:
            return error

        allowed_states = self._allowed_states()
        rows = self._parse_disk_rows(stdout)
        thresholds = {'disk_state_value': ','.join(allowed_states)}
        if not rows:
            return self.fail('storcli 출력 파싱 실패', message='Drive Information 출력에서 물리 디스크 행을 찾지 못했습니다.', stdout=stdout, thresholds=thresholds)

        invalid_rows = [row for row in rows if row['state'] not in allowed_states]
        metrics = {
            'disk_count': len(rows),
            'invalid_disk_count': len(invalid_rows),
            'invalid_disks': invalid_rows,
        }
        if invalid_rows:
            return self.fail(error='물리 디스크 State 값이 기준을 만족하지 않는 행이 있습니다.', metrics=metrics, thresholds=thresholds, reasons='물리 디스크 State 값이 기준을 만족하지 않는 행이 있습니다.', message='디스크 Fault 상태 경고: 비정상 디스크 %s개.' % len(invalid_rows))
        return self.ok(metrics=metrics, thresholds=thresholds, reasons='모든 물리 디스크 State 값이 기준을 만족합니다.', message='디스크 Fault 상태 점검 정상')


CHECK_CLASS = Check
