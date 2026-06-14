# type_name

일상점검

# area_name

server

# category_name

상태점검

# application_type

unix

# application

hpux

# inspection_code

HPUX-REPLAY-29

# is_required

권고

# inspection_name

Path 이중화 점검

# inspection_content

스토리지 디스크 경로 이중화 정상 여부를 점검한다.

# inspection_command

```bash
ioscan -m dsf
scsimgr get_info -D <ioscan에서 확인한 persistent_dsf>
```

# inspection_output

```text
Persistent DSF           Legacy DSF(s)
========================================
/dev/rdisk/disk1         /dev/rdsk/c2t0d0
                         /dev/rdsk/c3t0d0

STATUS INFORMATION FOR LUN : /dev/rdisk/disk1
Generic Status: OPTIMAL
Number of Paths: 2
```

# description

- `ioscan -m dsf`로 persistent DSF와 legacy DSF 매핑을 확인하고, 동일 LUN에 여러 경로가 있는지 확인한다.
- `ioscan -m dsf` 출력에서 확인되는 `/dev/rdisk/disk*` persistent DSF를 대상으로 `scsimgr get_info -D <persistent_dsf>`를 순차 실행한다.
- 각 LUN의 `Number of Paths`와 `Generic Status`를 확인하고, `ioscan -m dsf`의 legacy DSF 경로 수도 함께 비교한다.
- 경로 수가 기대보다 적거나 LUN 상태가 `OPTIMAL`이 아니면 SAN 경로 장애, zoning, 스토리지 포트 장애 가능성이 있다.
- HP-UX 버전과 스토리지 구성에 따라 `scsimgr` 지원 여부와 출력 형식이 다를 수 있다.

- **양호**: 모든 persistent DSF의 legacy DSF 경로 수와 `scsimgr` 경로 수가 기대값 이상이고 상태가 `OPTIMAL`인 경우
- **경고**: 하나 이상의 persistent DSF에서 경로 수 부족, 비정상 경로, LUN 상태 비정상이 확인되는 경우
- **확인 필요**: 경로 이중화 구성 기준이 없거나 명령이 지원되지 않는 경우

# thresholds

[
    {id: null, key: "expected_path_count", value: "3", sortOrder: 0}
,
{id: null, key: "required_lun_status", value: "OPTIMAL", sortOrder: 1}
]

# inspection_script

# -*- coding: utf-8 -*-

import re
import time
from collections import defaultdict

from .common._base import BaseCheck

CHECK_COMMAND = 'ioscan -m dsf'
BECOME_COMMAND_TIMEOUT = 1

class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_AUTH_TIMEOUT_SEC = 30

    def _is_become_enabled(self):
        value = self.get_connection_value('become', default=False)
        return str(value).strip().lower() in ('1', 'true', 'y', 'yes', 'on')

    def _build_become_command(self):
        if not self._is_become_enabled():
            return ''

        method = str(self.get_connection_value('become_method', default='su -') or 'su -')
        method = ' '.join(method.strip().lower().split())
        user = str(self.get_connection_value('become_user', default='root') or 'root').strip() or 'root'

        if method == 'su':
            return 'su ' + user
        if method == 'su -':
            return 'su - ' + user
        if method == 'sudo':
            return 'sudo -u ' + user + ' -i'
        raise ValueError(f'unsupported become_method: {method}')

    def _build_check_command(self, become_command):

        if become_command:
            become_password = self.get_connection_value('become_password', default='')    
            return [
                {
                    'command': become_command,
                    'timeout': BECOME_COMMAND_TIMEOUT,
                    'ignore_prompt': True,                    
                },
                {
                    'command': become_password,
                    'hide_command': True,
                },
                {
                    'command': CHECK_COMMAND,
                }
            ]
        else:
            return [{'command': CHECK_COMMAND}]

    def _parse_ioscan_m_dsf(self, output: str):
        disks = defaultdict(list)
        current_disk = None

        for line in output.splitlines():
            line = line.strip()

            if not line:
                continue

            if line.startswith("="):
                continue
            
            if "Persistent DSF" in line or "Legacy DSF" in line:
                continue

            persistent_match = re.search(r"(/dev/rdisk/disk\d+)", line)
            legacy_paths = re.findall(r"(/dev/rdsk/\S+)", line)

            if persistent_match:
                current_disk = persistent_match.group(1)

                for path in legacy_paths:
                    disks[current_disk].append(path)

                continue

            if current_disk and legacy_paths:
                for path in legacy_paths:
                    disks[current_disk].append(path)
        
        return dict(disks)

    def _check_multipath(self, disks: dict, min_path_count=3):
        results = []
        
        for disk, paths in disks.items():            
            path_count = len(paths)

            if path_count == 1:
                continue

            if path_count >= min_path_count:
                status = True                
            else:
                status = False
            
            results.append({
                "disk": disk,
                "path_count": path_count,
                "status": status,
                "paths": paths,
            })

        return results 

    def _find_check_result(self, results):
        for item in reversed(results):
            if item.get('command') == CHECK_COMMAND:
                return item
        return None

    def run(self):
        try:

            become_command = self._build_become_command()
            commands = self._build_check_command(become_command)

            results = self._run_paramiko_commands(commands)
            result = self._find_check_result(results)

            metrics = {}

            min_path_count = self.get_threshold_var(key='MIN_PATH_COUNT', default=3, value_type='int')

            if result is None:
                failed_result = next((item for item in results if item.get('rc') != 0), None)
                return self.fail(
                    error='명령 결과 없음',
                    message='명령 실행 결과를 찾지 못했습니다.',
                    stdout=(failed_result.get('stdout') or '').strip() if failed_result else '',
                    stderr=(failed_result.get('stderr') or '').strip() if failed_result else '',
                    metrics={
                        'executed_commands': [
                            item.get('display_command') or item.get('command')
                            for item in results
                        ],
                    },
                )

            output = result.get('stdout', '')            
            parsed = self._parse_ioscan_m_dsf(output=output)                      
            results = self._check_multipath(disks=parsed, min_path_count=min_path_count )                        

            if results:
                
                is_pass = all(item["status"] for item in results)                
                failed_items = [item for item in results if item["status"] is False]
                
                if is_pass:
                    return self.ok(
                        metrics = {"disk_count": len(results)},
                        reasons = f"모든 rdisk 디스크({len(results)})가 이중화 되어있습니다.",
                        message = f"모든 rdisk 디스크({len(results)})가 이중화 되어있습니다.",
                        )
                else:
                    return self.fail(
                        error="Path 이중화 점검 실패",
                        metrics = {"results": failed_items},                
                        message=f"Path 이중화 점검 실패: {failed_items}",                
                    )
            else:
                return self.fail(
                    error="Path 이중화 점검 실패",
                    message=f"Path 이중화 점검 실패: {results}",                
                )
        except Exception as e:
            import traceback

            return self.fail(
                error=f"Path 이중화 점검 실패: {str(traceback.print_exc())}",
                message=f"Path 이중화 점검 실패: {results}",                
            )

CHECK_CLASS = Check
