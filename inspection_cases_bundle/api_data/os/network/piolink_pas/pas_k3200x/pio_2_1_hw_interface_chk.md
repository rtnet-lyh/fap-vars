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

NETWORK-PIOLINK-PAS-K3200X-HW-INTERFACE-01

# is_required

필수

# inspection_name

인터페이스/모듈 상태

# inspection_content

각 인터페이스/Module Down/up 상태 점검 및 CRC error 증가 여부 확인

# inspection_command

```bash
show port
```

# inspection_output

```text

```

# description

- Link: 물리적인 링크 상태(= 실제 케이블/상대 장비 연결 상태)
- Status: 관리자(Admin) 설정 상태로, 포트를 사용 가능하게 설정했는지 여부

- **양호**: Link값이 'up'이고, Status값이 'enable'인 상태
- **경고**: Link값이 'down'이거나 Status값이 'disable'인 상태
- **확인 필요**: 명령어 수행 실패 또는 출력 결과를 확인할 수 없는 경우

# thresholds

[]

# inspection_script

# -*- coding: utf-8 -*-

from .common._base import BaseCheck


COMMAND = 'show port'


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

    def _parse_ports(self, text):
        ports = []
        skipped_non_physical = []
        for line in (text or '').splitlines():
            parts = line.split(None, 11)
            if len(parts) < 11:
                continue
            port = parts[0]
            link = parts[1].lower()
            status = parts[2].lower()
            if port.lower() == 'port' or link not in ('up', 'down', '--'):
                continue
            description = parts[11].strip() if len(parts) > 11 else ''
            row = {
                'port': port,
                'link': link,
                'status': status,
                'description': description,
            }
            if not port.isdigit():
                skipped_non_physical.append(row)
                continue
            row['used'] = status == 'enable' or bool(description)
            ports.append(row)
        return ports, skipped_non_physical

    def run(self):
        stdout, error = self._run_command()
        if error:
            return error

        ports, skipped_non_physical = self._parse_ports(stdout)
        if not ports:
            return self.fail('포트 상태 파싱 실패', message='show port 출력에서 물리 포트 상태 행을 찾지 못했습니다.', stdout=stdout)

        used_ports = [item for item in ports if item['used']]
        abnormal_ports = [
            item for item in used_ports
            if item['link'] != 'up' or item['status'] != 'enable'
        ]
        metrics = {
            'physical_port_count': len(ports),
            'used_port_count': len(used_ports),
            'abnormal_used_ports': abnormal_ports,
            'used_ports': used_ports,
            'skipped_non_physical_ports': skipped_non_physical,
        }
        if not used_ports:
            return self.fail('사용 포트 없음', message='show port 출력에서 사용 포트를 찾지 못했습니다.', stdout=stdout, metrics=metrics)
        if abnormal_ports:
            return self.warn(metrics=metrics, thresholds={}, reasons='사용 포트 중 Link up 또는 Status enable 조건을 만족하지 않는 포트가 있습니다.', message=f'인터페이스 상태 경고: 비정상 사용 포트 {len(abnormal_ports)}개.')
        return self.ok(metrics=metrics, thresholds={}, reasons='사용 포트의 Link가 up이고 Status가 enable입니다.', message=f'인터페이스/모듈 상태 점검 정상: 사용 포트 {len(used_ports)}개.')


CHECK_CLASS = Check
