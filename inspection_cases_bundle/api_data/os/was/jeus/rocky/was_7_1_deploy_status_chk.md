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

WAS-JEUS-ROCKY-REPLAY-016

# is_required

권고

# inspection_name

Deploy 상태 점검

# inspection_content

각 컨테이너별 Application Deploy 상태 확인(비정상시 특정서비스 불가)

# inspection_command

```bash
jeusadmin -u jeus -p jeus -f listApplications
```

# inspection_output

```text

```

# description

- Deployment Status: 애플리케이션 목록과 Deploy 상태 여부를 확인할 수 있음

# thresholds

[]

# inspection_script

# -*- coding: utf-8 -*-

from .common._base import BaseCheck

COMMAND = 'jeusadmin -u {user} -p {pw} -f listApplications'
# cd /home/exTMS;source .bash_profile;jeusadmin -u jeus -p jeus -f listApplications

class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'linux'
    PARAMIKO_REUSE_SESSION = False

    COMMAND_TIMEOUT = 20

    def _run_jeus_command(self, home_path, user, pw):
        command = f"cd {home_path};source .bash_profile;{COMMAND.format(user=user, pw=pw)}" 

        result = self._run_paramiko_commands([{
                    'command': command, 
                    'timeout': self.COMMAND_TIMEOUT
                },
            ],
            become=True,
            profile='linux',
        )[0]
        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()
        if result.get('rc') != 0:
            return stdout, stderr, self.fail(
                '점검 명령 실행 실패',
                message='JEUS 점검 명령 실행에 실패했습니다.',
                stdout=stdout,
                stderr=stderr,
            )
        return stdout, stderr, None

    def run(self):
        home_path = self.get_threshold_var(key='home_path', default='/home/exTMS', value_type='str')
        user = self.get_threshold_var(key='user', default='jeus', value_type='str')
        pw = self.get_threshold_var(key='pw', default='jeus', value_type='str')

        stdout, _stderr, error = self._run_jeus_command(home_path, user, pw)

        if error:
            return error
        if not stdout.strip():
            return self.fail('Deploy 상태 출력 없음', message='jeusadmin listApplications 출력이 비어 있습니다.', stdout=stdout)
        if 'connection failed' in stdout.lower() or 'fail to connect' in stdout.lower():
            return self.fail('jeusadmin 접속 실패', message='JEUS MBeanServer 접속에 실패했습니다.', stdout=stdout)
        app_lines = [line.strip() for line in stdout.splitlines() if '|' in line and 'Deployment Status' not in line and '---' not in line]
        not_deployed = [line for line in app_lines if 'not deployed' in line.lower()]
        deployed = [line for line in app_lines if 'deployed' in line.lower() and line not in not_deployed]
        metrics = {'application_count': len(app_lines), 'deployed_count': len(deployed), 'not_deployed_count': len(not_deployed), 'not_deployed_lines': not_deployed, 'application_lines': app_lines}
        thresholds = {'required_deployment_status': 'deployed'}
        if not_deployed:
            return self.warn(metrics=metrics, thresholds=thresholds, reasons='not deployed 상태 애플리케이션이 있습니다.', message='JEUS Deploy 상태 경고: not_deployed_count=%s' % len(not_deployed))
        return self.ok(metrics=metrics, thresholds=thresholds, reasons='애플리케이션이 deployed 상태입니다.', message='JEUS Deploy 상태 정상: deployed_count=%s' % len(deployed))

CHECK_CLASS = Check
