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


BK-NBU5240-002

# is_required

필수

# inspection_name

수행 결과 점검

# inspection_content

백업SW 로그 점검

# inspection_command

```bash
bpdbjobs | awk 'NR==1 || $2=="Backup"'
```

# inspection_output

```text
tggitsbackup:/home/maintenance # bpdbjobs | awk 'NR==1 || $2=="Backup"'
 JobID            Type      State Statu                    Policy   Schedule          Client         Started           Ended    Elapsed       Kilobytes KB Per Sec               Dest StUnit
 37320          Backup       Done     0              SDPOL-oracle       ARCH  polestar_TC-bk 05/26/2026 02:33:12 05/26/2026 02:34:29  000:01:17         7930720     114745     stu_disk_tggitsbackup
 37318          Backup       Done     0              SDPOL-oracle       DATA  polestar_TC-bk 05/26/2026 02:00:15 05/26/2026 02:33:12  000:32:57       225567840     114955     stu_disk_tggitsbackup
 37317          Backup       Done     0              SDPOL-oracle      start  polestar_TC-bk 05/26/2026 02:00:00 05/26/2026 02:05:17  000:05:17           14112         46     stu_disk_tggitsbackup
 37316          Backup       Done     0            polestar_TC-FS       Incr  polestar_TC-bk 05/26/2026 00:00:00 05/26/2026 00:05:49  000:05:49        38645216     113596     stu_disk_tggitsbackup
 37269          Backup       Done     0        polestar_TC-oracle       ARCH  polestar_TC-bk 05/25/2026 02:24:01 05/25/2026 02:26:57  000:02:56        19349792     114845     stu_disk_tggitsbackup
 37267          Backup       Done     0        polestar_TC-oracle       DATA  polestar_TC-bk 05/25/2026 02:00:15 05/25/2026 02:24:01  000:23:46       162479200     114958     stu_disk_tggitsbackup
 37266          Backup       Done     0        polestar_TC-oracle      start  polestar_TC-bk 05/25/2026 02:00:00 05/25/2026 02:05:19  000:05:19           13952         46     stu_disk_tggitsbackup
 37262          Backup       Done     0            polestar_TC-FS       Incr  polestar_TC-bk 05/25/2026 00:00:00 05/25/2026 00:05:49  000:05:49        38598880     113643     stu_disk_tggitsbackup
 37216          Backup       Done     0            polestar_TC-FS       Full  polestar_TC-bk 05/24/2026 00:00:00 05/24/2026 00:18:19  000:18:19       121952800     114345     stu_disk_tggitsbackup
```

# description

- 명령어: NetBackup 작업이력 및 작업 상태를 확인하는 명령어.
- awk 'NR==1 || $2=="Backup"' 옵션은 헤더라인과 Backup 문자열인 작업을 필터링 하기위해 사용함.
- State: Done이면 종료된 상태. Active면 수행 중 상태.
- Statu: 작업결과 코드, 0이면 정상완료 나머지 값은 실패 및 오류

- **양호**: 각 라인마다 State 값이 Done이고 Statu 값이 0인 상태.
- **경고**: 각 라인마다 State 값이 Done이 아니거나 Statu 값이 0이 아닌 상태.
- **확인 필요**: 명령어 실패 및 파싱 불가.

# thresholds

[]

# inspection_script

# -*- coding: utf-8 -*-

from .common._base import BaseCheck


COMMAND = "bpdbjobs | awk 'NR==1 || $2==\"Backup\"'"
STATE_VALUES = {'Active', 'Done', 'Queued', 'Requeued', 'Restarted', 'Suspended', 'Waiting'}


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
            [{'command': COMMAND, 'timeout': 10}],            
        )[0]
        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()
        if self._is_connection_error(result.get('rc'), stderr):
            return None, self.fail('호스트 연결 실패', message=stderr or 'Paramiko 연결 확인에 실패했습니다.', stderr=stderr)
        if result.get('rc') != 0:
            return None, self.fail('점검 명령 실행 실패', message='Backup 작업 상태 명령 실행에 실패했습니다.', stdout=stdout, stderr=stderr)
        return stdout, None

    def _parse_jobs(self, stdout):
        rows = []
        for line in str(stdout or '').splitlines():
            tokens = line.split()
            if not tokens or not tokens[0].isdigit():
                continue
            state_idx = next((idx for idx, token in enumerate(tokens[1:], 1) if token in STATE_VALUES), -1)
            if state_idx < 2 or state_idx + 1 >= len(tokens):
                continue
            rows.append({
                'job_id': tokens[0],
                'type': ' '.join(tokens[1:state_idx]),
                'state': tokens[state_idx],
                'status_code': tokens[state_idx + 1],
                'raw': line.strip(),
            })
        return rows

    def run(self):
        stdout, error = self._run_command()
        if error:
            return error

        rows = self._parse_jobs(stdout)
        if not rows:
            return self.fail('Backup 출력 파싱 실패', message='bpdbjobs 출력에서 Backup 작업 행을 찾지 못했습니다.', stdout=stdout)

        invalid_rows = [row for row in rows if row['state'] != 'Done' or row['status_code'] != '0']
        metrics = {
            'backup_job_count': len(rows),
            'invalid_job_count': len(invalid_rows),
            'invalid_jobs': invalid_rows,
        }
        thresholds = {'required_state': 'Done', 'required_status_code': '0'}
        if invalid_rows:
            return self.warn(metrics=metrics, thresholds=thresholds, reasons='Backup 작업 중 Done/0 기준을 만족하지 않는 행이 있습니다.', message='백업 작업 상태 경고: 비정상 작업 %s건.' % len(invalid_rows))
        return self.ok(metrics=metrics, thresholds=thresholds, reasons='모든 Backup 작업의 State가 Done이고 Statu 값이 0입니다.', message='백업 작업 상태 점검 정상')


CHECK_CLASS = Check
