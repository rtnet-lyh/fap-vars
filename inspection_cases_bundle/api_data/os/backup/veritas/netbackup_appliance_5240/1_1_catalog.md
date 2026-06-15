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


BK-NBU5240-001

# is_required

필수

# inspection_name

수행 결과 점검

# inspection_content

카탈로그 백업 상태 점검

# inspection_command

```bash
bpdbjobs | awk 'NR==1 || $2=="Catalog"'
```

# inspection_output

```text
netbackup:/home/maintenance # bpdbjobs | awk 'NR==1 || $2=="Catalog"'
 JobID            Type      State Statu                    Policy   Schedule          Client         Started           Ended    Elapsed       Kilobytes KB Per Sec               Dest StUnit
359517  Catalog Backup       Done     0                      CATALOG       full        netbackup 05/26/2026 12:00:37 05/26/2026 12:02:28  000:01:51         2237536      21669                      MSDP
359516  Catalog Backup       Done     0                      CATALOG       full        netbackup 05/26/2026 12:00:12 05/26/2026 12:00:24  000:00:12          375168     468960                      MSDP
359515  Catalog Backup       Done     0                      CATALOG       full        netbackup 05/26/2026 12:00:03 05/26/2026 12:00:36  000:00:33
359514  Catalog Backup       Done     0                      CATALOG          -        netbackup 05/26/2026 12:00:00 05/26/2026 12:02:28  000:02:28
359256  Catalog Backup       Done     0                      CATALOG       full        netbackup 05/25/2026 12:00:34 05/25/2026 12:02:10  000:01:36         2242016      25445                      MSDP
359255  Catalog Backup       Done     0                      CATALOG       full        netbackup 05/25/2026 12:00:09 05/25/2026 12:00:22  000:00:13          375168     248291                      MSDP
359254  Catalog Backup       Done     0                      CATALOG       full        netbackup 05/25/2026 12:00:04 05/25/2026 12:00:33  000:00:29
359253  Catalog Backup       Done     0                      CATALOG          -        netbackup 05/25/2026 12:00:00 05/25/2026 12:02:10  000:02:10
358996  Catalog Backup       Done     0                      CATALOG       full        netbackup 05/24/2026 12:00:41 05/24/2026 12:02:04  000:01:23         2287904      30443                      MSDP
358995  Catalog Backup       Done     0                      CATALOG       full        netbackup 05/24/2026 12:00:15 05/24/2026 12:00:30  000:00:15          375168     326801                      MSDP
```

# description

- 명령어: NetBackup 작업이력 및 작업 상태를 확인하는 명령어.
- awk 'NR==1 || $2=="Catalog"' 옵션은 헤더라인과 Type이 Catalog Backup인 작업을 필터링 하기위해 사용함.
- State: Done이면 종료된 상태. Active면 수행 중 상태.
- Statu: 작업결과 코드, 0이면 정상완료 나머지 값은 실패 및 오류

[참고]
- Catalog Backup: Netbackup 구성, 정책정보, 이미지 카탈로그 등 백업 복구에 필요한 핵심 메타 데이터를 보고하기 위한 백업 작업.

- **양호**: 각 라인마다 State 값이 Done이고 Statu 값이 0인 상태.
- **경고**: 각 라인마다 State 값이 Done이 아니거나 Statu 값이 0이 아닌 상태.
- **확인 필요**: 명령어 실패 및 파싱 불가.

# thresholds

[]

# inspection_script

# -*- coding: utf-8 -*-

from .common._base import BaseCheck


COMMAND = "bpdbjobs | awk 'NR==1 || $2==\"Catalog\"'"
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
            [{'command': COMMAND, 'timeout': 3}],            
        )[0]
        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()
        if self._is_connection_error(result.get('rc'), stderr):
            return None, self.fail('호스트 연결 실패', message=stderr or 'Paramiko 연결 확인에 실패했습니다.', stderr=stderr)
        if result.get('rc') != 0:
            return None, self.fail('점검 명령 실행 실패', message='Catalog Backup 작업 상태 명령 실행에 실패했습니다.', stdout=stdout, stderr=stderr)
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
            return self.fail('Catalog Backup 출력 파싱 실패', message='bpdbjobs 출력에서 Catalog Backup 작업 행을 찾지 못했습니다.', stdout=stdout)

        invalid_rows = [row for row in rows if row['state'] != 'Done' or row['status_code'] != '0']
        metrics = {
            'catalog_backup_job_count': len(rows),
            'invalid_job_count': len(invalid_rows),
            'invalid_jobs': invalid_rows,
        }
        thresholds = {'required_state': 'Done', 'required_status_code': '0'}
        if invalid_rows:
            return self.fail(
                error='Catalog Backup 작업 중 Done/0 기준을 만족하지 않는 행이 있습니다.', 
                metrics=metrics, 
                thresholds=thresholds, 
                reasons='Catalog Backup 작업 중 Done/0 기준을 만족하지 않는 행이 있습니다.', 
                message='카탈로그 백업 상태 경고: 비정상 작업 %s건.' % len(invalid_rows)
            )
        return self.ok(
            metrics=metrics, 
            thresholds=thresholds, 
            reasons='모든 Catalog Backup 작업의 State가 Done이고 Statu 값이 0입니다.', 
            message='카탈로그 백업 상태 점검 정상'
        )


CHECK_CLASS = Check
