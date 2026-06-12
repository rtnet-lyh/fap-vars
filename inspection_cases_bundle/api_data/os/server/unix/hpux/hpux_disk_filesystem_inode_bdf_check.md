# type_name

일상점검

# area_name

상태점검

# category_name

server

# application_type

unix

# application

hpux

# inspection_code

HPUX-REPLAY-05

# is_required

권고

# inspection_name

I-Node 사용률

# inspection_content

파일시스템별 inode 사용률을 점검한다.

# inspection_command

```bash
bdf -i
```

# inspection_output

```text
Filesystem          kbytes    used   avail %used iused ifree %iuse Mounted on
/dev/vg00/lvol3   20971520  8300000 12671520  40%  4210 95000    5% /
/dev/vg00/lvol4   52428800 42000000 10428800  80% 81200 18800   81% /opt
/dev/vg00/lvol5  104857600 70000000 34857600  67% 14300 85700   15% /var
```

# description

- `bdf -i` 명령으로 파일시스템별 inode 사용량을 확인한다.
- inode 사용률이 높으면 디스크 용량이 남아 있어도 새 파일을 생성하지 못할 수 있다.
- 임시 파일, 로그 파일, 세션 파일처럼 작은 파일이 대량 생성되는 경로를 우선 확인한다.
- HP-UX 파일시스템 종류와 버전에 따라 inode 표시 컬럼이 다를 수 있으므로 출력 형식을 함께 검토한다.

- **양호**: 모든 운영 대상 파일시스템의 inode 사용률이 `INODE_USED_MAX_PCT` 미만인 경우
- **경고**: inode 사용률이 `INODE_USED_MAX_PCT` 이상인 파일시스템이 있는 경우
- **확인 필요**: `bdf -i` 결과에서 inode 정보를 확인할 수 없는 경우

# thresholds

[
    {id: null, key: "INODE_USED_MAX_PCT", value: "80", sortOrder: 0}
]

# inspection_script

# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


CHECK_COMMAND = 'bdf -i'
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
        become_password = self.get_connection_value('become_password', default='')                                        
        become_base_command = [
            {
                'command': become_command,
                'timeout': BECOME_COMMAND_TIMEOUT,
                'ignore_prompt': True,                    
            },
            {
                'command': become_password,
                'hide_command': True,
            }
        ]        
        if become_command:            
            become_base_command.append({"command": CHECK_COMMAND})
            return become_base_command
        else:
            return [{
                "command": CHECK_COMMAND
            }]

    def _find_check_result(self, results):
        for item in reversed(results):
            if item.get('command') == CHECK_COMMAND:
                return item
        return None

    def _parse_bdf(self, output: str, threshold: int):              
        pattern = re.compile(
            r"^/dev/\S+.*(?P<iuse>\d+)%\s+(?P<mount>/\S*)$",
            re.MULTILINE
        )
        results = []

        for match in pattern.finditer(output):
            iuse = int(match.group("iuse"))
            mount = match.group("mount")

            results.append({
                "mount": mount,
                "iused_percent": iuse,
                "ok": iuse <threshold
            })

        return results

    def run(self):
        try:
            metrics = {}

            max_usage = self.get_threshold_var(key='MAX_USAGE', default=80, value_type='int')

            become_command = self._build_become_command()            
            check_commands = self._build_check_command(become_command)                        
            results = self._run_paramiko_commands(check_commands)            
            result = self._find_check_result(results)            
            output = result.get('stdout', '')

            parsed = self._parse_bdf(output=output, threshold=max_usage)
            metrics = parsed
            fail_items = [item for item in parsed if not item["ok"]]

            avg_iused = round(
                sum(item["iused_percent"] for item in parsed) / len(parsed),
                2
            )
            metrics.append({"avg_iused": avg_iused})

            is_pass = True if not fail_items else False

            if is_pass:                
                return self.ok(
                    metrics = metrics,
                    reasons = f"iused 사용량이 정상입니다. 평균: {avg_iused}% / 임계치: {max_usage}%",
                    message = f"iused 사용량이 정상입니다. 평균: {avg_iused}% / 임계치: {max_usage}%",
                )
            else:
                return self.fail(
                    error="iused 사용량 점검 실패",
                    metrics = metrics,          
                    message = f"iused 사용량이 비정상입니다. 평균: {avg_iused}% / 임계치: {max_usage}%",
                )
            
        except Exception as e:    
            import traceback
            traceback.print_exc()
            return self.fail(
                error=f"iused 사용량 점검 실패: {str(e)}",
                message=f"iused 사용량 점검 실패: {str(e)}",                
            )

CHECK_CLASS = Check
