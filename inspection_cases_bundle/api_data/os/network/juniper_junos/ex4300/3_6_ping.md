# type_name

일상점검

# area_name

상태점검

# category_name

network

# application_type

juniper_junos

# application

ex4300

# inspection_code

NETWORK-JUNIPER-JUNOS-EX4300-3-6-PING

# is_required

권고

# inspection_name

통신 테스트

# inspection_content

특정 장비와 통신상태 정상 확인.

# inspection_command

```bash
ping `ping_ip` count 5
```

# inspection_output

```text

```

# description

- 명령어: 특정 대상 IP와 통신 가능여부를 5회 확인하는 명령어.
- 해당 장비에서 ping 명령어 사용 불가

- **양호**: 
- **경고**: 
- **확인 필요**: 명령어 실패, 파싱 불가

# thresholds

[
    {id: null, key: "ping_ip", value: "172.18.8.191", sortOrder: 0}
]

# inspection_script

# -*- coding: utf-8 -*-

from .common._base import BaseCheck


COMMAND_ERROR_MARKERS = ('syntax error', 'unknown command', 'invalid command', 'unknown keyword', 'missing argument')
COMMAND_TEMPLATE = 'ping {ping_ip} count 5'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'generic_network'
    PARAMIKO_REUSE_SESSION = True

    # def _run_command(self, command):
    #     results = self._run_paramiko_commands([command], profile=self.PARAMIKO_PROFILE)
    #     if not results:
    #         return None, self.fail('점검 명령 실행 실패', message='Paramiko 명령 실행 결과가 비어 있습니다.')
    #     result = results[0]
    #     stdout = (result.get('stdout') or '').strip()
    #     stderr = (result.get('stderr') or '').strip()
    #     if result.get('rc') != 0:
    #         return None, self.fail('점검 명령 실행 실패', message=f'{command} 명령 실행에 실패했습니다.', stdout=stdout, stderr=stderr)
    #     error_text = self._detect_cli_error(stdout, stderr)
    #     if error_text:
    #         return None, self.fail('점검 명령 실행 실패', message=f'{command} 명령 출력에서 오류가 확인되었습니다: {error_text}', stdout=stdout, stderr=stderr)
    #     return stdout, None

    # def _detect_cli_error(self, *texts):
    #     for text in texts:
    #         for line in str(text or '').splitlines():
    #             stripped = line.strip()
    #             lowered = stripped.lower()
    #             if stripped and any(marker in lowered for marker in COMMAND_ERROR_MARKERS):
    #                 return stripped
    #     return ''

    def run(self):
        # ping_ip = str(self.get_threshold_var('ping_ip', default='172.18.8.191', value_type='str')).strip()
        # thresholds = {'ping_ip': ping_ip}
        # if not ping_ip:
        #     return self.fail('임계치 미정의', message='ping_ip threshold 값이 필요합니다.', thresholds=thresholds)

        # stdout, error = self._run_command(COMMAND_TEMPLATE.format(ping_ip=ping_ip))
        # if error:
        #     return error
        return self.ok(reasons='ping 명령어 수행 불가 장비', message='ping 명령어 수행 불가 장비')


CHECK_CLASS = Check
