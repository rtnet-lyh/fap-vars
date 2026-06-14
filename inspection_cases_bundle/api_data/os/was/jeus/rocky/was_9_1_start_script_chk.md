# type_name

일상점검

# area_name

was

# category_name

상태점검

# application_type

jeus

# application

rocky

# inspection_code

WAS-JEUS-ROCKY-REPLAY-018

# is_required

권고

# inspection_name

기동 스크립트 확인

# inspection_content

각 인스턴스별 기동 스크립트 변경 여부 확인

# inspection_command

```bash

```

# inspection_output

```text
[exTMS@tips_was1:/home/exTMS/tmax/jeus/bin]$ stat /home/exTMS/tmax/jeus/bin/startDomainAdminServer
  File: /home/exTMS/tmax/jeus/bin/startDomainAdminServer
  Size: 3507            Blocks: 8          IO Block: 4096   일반 파일
Device: fd00h/64768d    Inode: 37690590    Links: 1
Access: (0700/-rwx------)  Uid: ( 1001/   exTMS)   Gid: ( 1001/   exTMS)
Context: unconfined_u:object_r:user_home_t:s0
Access: 2026-05-15 15:51:28.263962332 +0900
Modify: 2025-07-25 11:22:36.982827460 +0900
Change: 2025-07-25 11:22:36.982827460 +0900
 Birth: 2025-07-25 11:22:36.982827460 +0900
```

# description

- 기동 스크립트의 파일 상태 정보를 확인하여, 수정 시간, 액세스 시간, 생성 시간 등을 포함한 정보를 확인할 수 있음. 이를 통해 스크립트 변경 여부를 확인할 수 있음.

# thresholds

[]

# inspection_script

# -*- coding: utf-8 -*-

from .common._base import BaseCheck

class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'linux'
    PARAMIKO_REUSE_SESSION = False

    COMMAND_TIMEOUT = 1

    def _run_jeus_command(self, home_path, target_file):
        command = f"cd {home_path};source .bash_profile;stat $JEUS_HOME/bin/{target_file}" 

        result = self._run_paramiko_commands(
            [{'command': command, 'timeout': self.COMMAND_TIMEOUT}],
            become=True,
            profile='linux',
        )[0]
        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()
        
        if result.get('rc') not in [0, 124]:
            return stdout, stderr, self.fail(
                '점검 명령 실행 실패',
                message='JEUS 점검 명령 실행에 실패했습니다.',
                stdout=stdout,
                stderr=stderr,
            )
        return stdout, stderr, None

    def run(self):
        home_path = self.get_threshold_var(key='home_path', default='/home/exTMS', value_type='str')
        target_file = self.get_threshold_var(key='target_file', default='startDomainAdminServer', value_type='str')

        stdout, _stderr, error = self._run_jeus_command(home_path, target_file)
        if error:
            return error
        metrics = {
            'has_file': 'File:' in stdout, 
            'has_access': 'Access:' in stdout, 
            'has_modify': 'Modify:' in stdout, 
            'has_change': 'Change:' in stdout,
        }
        thresholds = {'required_fields': ['File', 'Access', 'Modify', 'Change']}
        if not all(metrics.values()):
            return self.fail('stat 출력 파싱 실패', message='stat 출력에서 File/Access/Modify/Change 값을 모두 확인하지 못했습니다.', stdout=stdout, metrics=metrics, thresholds=thresholds)
        return self.ok(metrics=metrics, thresholds=thresholds, reasons='기동 스크립트 stat 정보를 확인했습니다.', message='JEUS 기동 스크립트 stat 확인 정상')


CHECK_CLASS = Check
