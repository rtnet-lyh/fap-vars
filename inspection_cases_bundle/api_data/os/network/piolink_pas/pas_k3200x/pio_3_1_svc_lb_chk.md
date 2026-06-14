# type_name

일상점검

# area_name

network

# category_name

상태점검

# application_type

piolink_pas

# application

pas_k3200x

# inspection_code

NETWORK-PIOLINK-PAS-K3200X-SERVICE-LB-01

# is_required

권고

# inspection_name

각 LB 상태 확인

# inspection_content

부하 분산 상태 점검 및 real 서버 Health-Check 상태 점검

# inspection_command

```bash
show real
```

# inspection_output

```text

```

# description

※ show real: LB에 등록된 Real Server 상태를 조회하는 명령
- RIP: Real Server IP
- Status: LB 서비스 활성 상태(enable/disable) 의미
- Weight: 부하분산 가중치
- Backup: Backup Server 여부
- Name: Real Server 이름, - 인 경우 이름(alias)이 미설정된 상태를 의미

- **양호**: 모든 Real Server의 Status 값이 'enable'인 상태
- **경고**: 'disable' 상태의 Real Server가 존재하는 상태
- **확인 필요**: 명령어 수행 실패 또는 출력 결과를 확인할 수 없는 경우

# thresholds

[]

# inspection_script

# -*- coding: utf-8 -*-

from .common._base import BaseCheck


COMMAND = 'show real'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'generic_network'
    PARAMIKO_REUSE_SESSION = True

    def _run_command(self):
        results = self._run_paramiko_commands([COMMAND], profile=self.PARAMIKO_PROFILE)
        if not results:
            return None, self.fail('점검 명령 실행 실패', message='Paramiko 명령 실행 결과가 비어 있습니다.')
        result = results[0]
        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()
        if result.get('rc') != 0:
            return None, self.fail('점검 명령 실행 실패', message=f'{COMMAND} 명령 실행에 실패했습니다.', stdout=stdout, stderr=stderr)
        return stdout, None

    def _parse_real_servers(self, text):
        servers = []
        for line in (text or '').splitlines():
            parts = line.split()
            if len(parts) < 4 or not parts[0].isdigit():
                continue
            servers.append({
                'id': int(parts[0]),
                'status': parts[-1].lower(),
                'raw': line.strip(),
            })
        return servers

    def run(self):
        stdout, error = self._run_command()
        if error:
            return error

        servers = self._parse_real_servers(stdout)
        if not servers:
            return self.fail('Real Server 파싱 실패', message='show real 출력에서 Real Server 행을 찾지 못했습니다.', stdout=stdout)

        disabled_servers = [item for item in servers if item['status'] != 'enable']
        metrics = {
            'real_server_count': len(servers),
            'disabled_real_servers': disabled_servers,
            'real_servers': servers,
        }
        if disabled_servers:
            return self.fail(error="Status가 enable이 아닌 Real Server가 있습니다.", metrics=metrics, thresholds={}, reasons='Status가 enable이 아닌 Real Server가 있습니다.', message=f'LB 상태 경고: 비정상 Real Server {len(disabled_servers)}개.')
        return self.ok(metrics=metrics, thresholds={}, reasons='모든 Real Server Status가 enable입니다.', message=f'LB 상태 점검 정상: Real Server {len(servers)}개.')


CHECK_CLASS = Check
