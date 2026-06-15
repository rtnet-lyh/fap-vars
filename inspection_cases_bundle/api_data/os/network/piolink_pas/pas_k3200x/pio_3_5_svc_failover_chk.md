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


NW-PIO-K3200X-010

# is_required

권고

# inspection_name

이중화 구성 상태 점검

# inspection_content

Failover 상태 확인

# inspection_command

```bash
show failover
```

# inspection_output

```text

```

# description

- show failover 명령을 통해 이중화(Failover) 및 VRRP 상태를 확인
- Mode: Active/Standby 구성 여부를 확인
- Running: 현재 장비 역할(Master/backup)을 확인
- Status: Vrrp 활성 상태(enable/disable)를 확인 
- VIP(Virtual IP): 이중화 장비 간 공유되는 가상 IP 의미
- 장애 발생 시 다른 장비로 서비스가 자동 절체(Failover) 되는지 확인 가능

- **양호**: Status 값이 'enable'이며 Runinng 값이 master 또는 backup 상태 
- **경고**: Status 값이 'disable'이며 Runinn g값이 비정상인 상태
- **확인 필요**: 명령어 수행 실패 또는 출력 결과를 확인할 수 없는 경우
※참고: 이중화 구성 정상 여부는 양쪽 장비의 Running(Master/backup) 상태를 함께 확인해야 함

# thresholds

[]

# inspection_script

# -*- coding: utf-8 -*-

from .common._base import BaseCheck


COMMAND = 'show failover'


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

    def _parse_vrrp_rows(self, text):
        rows = []
        for line in (text or '').splitlines():
            parts = line.split()
            if len(parts) < 4 or not parts[0].isdigit():
                continue
            running = parts[2].lower()
            status = parts[3].lower()
            rows.append({
                'vrid': parts[0],
                'mode': parts[1],
                'running': running,
                'status': status,
                'raw': line.strip(),
            })
        return rows

    def run(self):
        stdout, error = self._run_command()
        if error:
            return error

        vrrp_rows = self._parse_vrrp_rows(stdout)
        if not vrrp_rows:
            return self.fail('VRRP 상태 파싱 실패', message='show failover 출력에서 VRRP 행을 찾지 못했습니다.', stdout=stdout)

        invalid_rows = [
            item for item in vrrp_rows
            if item['running'] not in ('master', 'backup') or item['status'] != 'enable'
        ]
        metrics = {
            'vrrp_count': len(vrrp_rows),
            'invalid_vrrp_rows': invalid_rows,
            'vrrp_rows': vrrp_rows,
        }
        if invalid_rows:
            return self.fail(error='VRRP Running 또는 Status 기준을 만족하지 않는 행이 있습니다.', metrics=metrics, thresholds={}, reasons='VRRP Running 또는 Status 기준을 만족하지 않는 행이 있습니다.', message=f'Failover 상태 경고: 비정상 VRRP {len(invalid_rows)}개.')
        return self.ok(metrics=metrics, thresholds={}, reasons='VRRP Running이 master/backup이고 Status가 enable입니다.', message=f'Failover 상태 점검 정상: VRRP {len(vrrp_rows)}개.')


CHECK_CLASS = Check
