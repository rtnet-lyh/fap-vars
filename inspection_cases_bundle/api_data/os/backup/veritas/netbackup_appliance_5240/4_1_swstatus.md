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

BACKUP-VERITAS-NBU5240-REPLAY-010

# is_required

필수

# inspection_name

SW 상태 점검

# inspection_content

백업 Process, 백업 Client 연결 상태 등 점검

# inspection_command

```bash
bpdbjobs
```

# inspection_output

```text
atmsbackup:/home/maintenance # bpdbjobs
 JobID            Type      State Statu                    Policy   Schedule          Client         Started           Ended    Elapsed       Kilobytes KB Per Sec               Dest StUnit
 57181    Image Delete       Done     0                                                      05/26/2026 16:39:45 05/26/2026 16:39:51  000:00:06
 57180          Backup       Done     0              VM_TIPS_WAS1       full       tips_was1 05/26/2026 15:30:16 05/26/2026 16:39:37  001:09:21       129830560      31534                      MSDP
 57179        Snapshot       Done     0              VM_TIPS_WAS1          -       tips_was1 05/26/2026 15:30:00 05/26/2026 16:39:45  001:09:45                                                 MSDP
 57178    Image Delete       Done     0                                                      05/26/2026 14:15:19 05/26/2026 14:15:28  000:00:09
 57177          Backup       Done     0              VM_TIPS_WAS2       full       tips_was2 05/26/2026 13:30:17 05/26/2026 14:15:11  000:44:54        86671552      32458                      MSDP
 57176        Snapshot       Done     0              VM_TIPS_WAS2          -       tips_was2 05/26/2026 13:30:00 05/26/2026 14:15:19  000:45:19                                                 MSDP
 57175  Catalog Backup       Done     0                   CATALOG       full      atmsbackup 05/26/2026 12:00:36 05/26/2026 12:05:07  000:04:31        10674208      40994                      MSDP
 57174  Catalog Backup       Done     0                   CATALOG       full      atmsbackup 05/26/2026 12:00:11 05/26/2026 12:00:27  000:00:16          238528     140724                      MSDP
 57173  Catalog Backup       Done     0                   CATALOG       full      atmsbackup 05/26/2026 12:00:04 05/26/2026 12:00:35  000:00:31
 57172  Catalog Backup       Done     0                   CATALOG          -      atmsbackup 05/26/2026 12:00:00 05/26/2026 12:05:11  000:05:11
 57171    Image Delete       Done     0                                                      05/26/2026 11:00:27 05/26/2026 11:00:38  000:00:11
 57170          Backup       Done     0 VRTS_NBA_Dedupe_Catalog_atmsbackup       Full      atmsbackup 05/26/2026 11:00:00 05/26/2026 11:00:25  000:00:25          113888      10163                      MSDP
```

# description

- 명령어: RAID 컨트롤러에 연결된 전체 물리 디스크 상태를 확인하는 명령어.

[참고]
- 다른 값에 스페이스 들어간 값이 많아 파싱 시 고정 컬럼위치만으로 판단하지 않도록 주의 필요.

- **양호**: 'State' 컬럼 값이 Done이며 'Statu' 값이 0인 상태.
- **경고**: 'State' 값이 Done이 아니거나 'Statu' 값이 0이 아닌 상태.
- **확인 필요**: 명령어 실패 및 파싱 불가.

# thresholds

[]

# inspection_script

# -*- coding: utf-8 -*-

from .common._base import BaseCheck


COMMAND = 'bpdbjobs'
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
            return None, self.fail('점검 명령 실행 실패', message='백업 SW 작업 상태 조회 명령 실행에 실패했습니다.', stdout=stdout, stderr=stderr)
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
            return self.fail('bpdbjobs 출력 파싱 실패', message='bpdbjobs 출력에서 작업 행을 찾지 못했습니다.', stdout=stdout)

        invalid_rows = [row for row in rows if row['state'] != 'Done' or row['status_code'] not in ['0', '71']]
        metrics = {
            'job_count': len(rows),
            'invalid_job_count': len(invalid_rows),
            'invalid_jobs': invalid_rows,
        }
        thresholds = {'required_state': 'Done', 'required_status_code': '0'}
        if invalid_rows:
            return self.fail(error='백업 SW 작업 중 Done/0 기준을 만족하지 않는 행이 있습니다.', metrics=metrics, thresholds=thresholds, reasons='백업 SW 작업 중 Done/0 기준을 만족하지 않는 행이 있습니다.', message='백업 SW 상태 경고: 비정상 작업 %s건.' % len(invalid_rows))
        return self.ok(metrics=metrics, thresholds=thresholds, reasons='모든 백업 SW 작업의 State가 Done이고 Statu 값이 0입니다.', message='백업 SW 상태 점검 정상')


CHECK_CLASS = Check
