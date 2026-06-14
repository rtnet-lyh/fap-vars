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

HPUX-REPLAY-09

# is_required

권고

# inspection_name

Disk 인식여부 점검

# inspection_content

디스크 장치의 OS 인식 정상 여부를 점검한다.

# inspection_command

```bash
ioscan -fnC disk
```

# inspection_output

```text
Class     I  H/W Path        Driver   S/W State   H/W Type     Description
=========================================================================
disk      0  0/1/1/0.0.0     sdisk    CLAIMED     DEVICE       HP LOGICAL VOLUME
          /dev/dsk/c0t0d0    /dev/rdsk/c0t0d0
disk      1  0/1/1/0.1.0     sdisk    CLAIMED     DEVICE       HP LOGICAL VOLUME
          /dev/dsk/c1t0d0    /dev/rdsk/c1t0d0
```

# description

- `ioscan -fnC disk` 명령으로 OS가 인식한 디스크 장치와 디바이스 파일을 확인한다.
- 운영에 필요한 디스크가 `CLAIMED` 상태로 표시되고 `/dev/dsk`, `/dev/rdsk` 경로가 생성되어 있으면 정상으로 본다.
- `UNCLAIMED`, `NO_HW`, `ERROR` 상태나 기대 디스크 누락은 디스크, HBA, SAN, 스토리지 매핑 문제 가능성이 있다.
- 신규 디스크 추가 후에는 필요 시 `insf -e` 실행 여부와 장치 파일 생성을 확인한다.

- **양호**: 필수 디스크가 모두 `CLAIMED` 상태로 인식되는 경우
- **경고**: 필수 디스크 누락 또는 `UNCLAIMED`, `NO_HW`, `ERROR` 상태가 있는 경우
- **확인 필요**: 기대 디스크 목록이 없거나 스토리지 구성 정보가 불명확한 경우

# thresholds

[
    {id: null, key: "expected_disk_count", value: "0", sortOrder: 0}
,
{id: null, key: "allowed_disk_states", value: "CLAIMED", sortOrder: 1}
]

# inspection_script

# -*- coding: utf-8 -*-

import re
import time

from .common._base import BaseCheck

CHECK_COMMAND = 'ioscan -fnC disk'
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

    def _find_check_result(self, results):
        for item in reversed(results):
            if item.get('command') == CHECK_COMMAND:
                return item
        return None

    def _parse_hpux_disk_ioscan(self, output: str, ok_keyword: str):
        # VMS2:root[/]# ioscan -fnC disk
        # Class     I  H/W Path        Driver S/W State   H/W Type     Description
        # ========================================================================
        # disk      0  0/0/0/1/0/0/0.0.0              sdisk   CLAIMED     DEVICE       HP      LOGICAL VOLUME
        #                             /dev/dsk/c0t0d0     /dev/dsk/c0t0d0s2   /dev/rdsk/c0t0d0    /dev/rdsk/c0t0d0s2
        #                             /dev/dsk/c0t0d0s1   /dev/dsk/c0t0d0s3   /dev/rdsk/c0t0d0s1  /dev/rdsk/c0t0d0s3
        # disk      1  0/0/0/1/0/0/0.0.1              sdisk   CLAIMED     DEVICE       HP      LOGICAL VOLUME
        #                             /dev/dsk/c0t0d1   /dev/rdsk/c0t0d1
        # disk    3085  0/0/0/1/0/0/0.0.2              sdisk   CLAIMED     DEVICE       HP      LOGICAL VOLUME
        #                             /dev/dsk/c0t0d2     /dev/dsk/c0t0d2s2   /dev/rdsk/c0t0d2    /dev/rdsk/c0t0d2s2
        #                             /dev/dsk/c0t0d2s1   /dev/dsk/c0t0d2s3   /dev/rdsk/c0t0d2s1  /dev/rdsk/c0t0d2s3
        # disk    662  0/0/0/9/0/0/0.207.31.0.0.0.1   sdisk   CLAIMED     DEVICE       3PARdataVV
        #                             /dev/dsk/c34t0d1   /dev/rdsk/c34t0d1
        # disk    663  0/0/0/9/0/0/0.207.31.0.0.0.2   sdisk   CLAIMED     DEVICE       3PARdataVV
        #                             /dev/dsk/c34t0d2   /dev/rdsk/c34t0d2
        # disk    664  0/0/0/9/0/0/0.207.31.0.0.0.3   sdisk   CLAIMED     DEVICE       3PARdataVV
        #                             /dev/dsk/c34t0d3   /dev/rdsk/c34t0d3
        # disk    665  0/0/0/9/0/0/0.207.31.0.0.0.4   sdisk   CLAIMED     DEVICE       3PARdataVV
        #                             /dev/dsk/c34t0d4   /dev/rdsk/c34t0d4
        # disk    666  0/0/0/9/0/0/0.207.31.0.0.0.5   sdisk   CLAIMED     DEVICE       3PARdataVV
        #                             /dev/dsk/c34t0d5   /dev/rdsk/c34t0d5
        # disk    667  0/0/0/9/0/0/0.207.31.0.0.0.6   sdisk   CLAIMED     DEVICE       3PARdataVV
        #                             /dev/dsk/c34t0d6   /dev/rdsk/c34t0d6

        pattern = re.compile(
            r"^disk\s+"            
            r"(?P<instance>\d+)\s+"
            r"(?P<hw_path>\S+)\s+"
            r"(?P<driver>\S+)\s+"
            r"(?P<state>\S+)\s+"
            r"(?P<hw_type>\S+)\s+",
            re.MULTILINE
        )

        results = []

        for match in pattern.finditer(output):
            item = match.groupdict()

            item["ok"] = item["state"] == ok_keyword

            results.append(item)

        return results

    def run(self):
        try:

            become_command = self._build_become_command()
            commands = self._build_check_command(become_command)

            results = self._run_paramiko_commands(commands)
            result = self._find_check_result(results)

            metrics = {}

            ok_keyword = self.get_threshold_var(key='OK_KEYWORD', default='CLAIMED', value_type='float')

            output = result.get('stdout', '')            
            parsed = self._parse_hpux_disk_ioscan(
                output=output,
                ok_keyword=ok_keyword,                
            )

            ok_items = [item for item in parsed if item.get("ok", False)]
            fail_items = [item for item in parsed if not item.get("ok", False)]

            is_pass = True if ok_items and not fail_items else False

            metrics["disk_count"] = len(parsed)
            metrics["ok_count"] = len(ok_items)
            metrics["fail_count"] = len(fail_items)
            metrics["fail_items"] = fail_items
            metrics["is_pass"] = is_pass
                
            if is_pass:
                return self.ok(
                    metrics = metrics,
                    reasons = f"DISK 인식 상태가 정상입니다. {metrics}",
                    message = f"DISK 인식 상태가 정상입니다. {metrics}",
                )
            else:
                return self.fail(
                    error="DISK 인식 상태 불량",                        
                    metrics = metrics,
                    reasons = f"DISK 인식 상태 점검이 필요 합니다. {metrics}",
                    message = f"DISK 인식 상태 점검이 필요 합니다. {metrics}",
                )

        except Exception as e:
            return self.fail(
                error=f"DISK 인식 상태 점검 실패: {str(e)}",
                message=f"DISK 인식 상태 점검 실패: {str(e)}",                
            )

CHECK_CLASS = Check
