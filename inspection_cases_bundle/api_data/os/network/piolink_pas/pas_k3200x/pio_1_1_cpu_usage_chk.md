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


NW-PIO-K3200X-001

# is_required

필수

# inspection_name

CPU 사용률

# inspection_content

라우터, 스위치 등의 네트워크 장비가 사용하는 CPU자원 사용률 확인

# inspection_command

```bash
show resource
```

# inspection_output

```text

```

# description

- CPU Usage : CPU 자원 사용률

- **양호**: CPU Usage 값이 `max_used_percent`를 초과하지 않는 상태
- **경고**: CPU Usage 값이 `max_used_percent`를 초과한 상태
- **확인 필요**: 명령어 수행 실패 또는 출력 결과를 확인할 수 없는 경우

# thresholds

[
    {id: null, key: "max_used_percent", value: "1", sortOrder: 0}
]

# inspection_script

# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


COMMAND = 'show resource'
USAGE_RE = re.compile(r'Usage\s*:\s*([0-9.]+)\s*%')


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

    def _parse_cpu_usage(self, text):
        processor = ''
        section = ''
        values = []
        for line in (text or '').splitlines():
            stripped = line.strip()
            if not stripped or set(stripped) <= {'=', '-'}:
                continue
            if stripped in ('Management Processor', 'Packet Processor'):
                processor = stripped
                section = ''
                continue
            if stripped in ('CPU', 'Memory'):
                section = stripped
                continue
            if section == 'CPU':
                match = USAGE_RE.search(stripped)
                if match:
                    values.append({
                        'processor': processor or 'unknown',
                        'used_percent': round(float(match.group(1)), 2),
                    })
                    section = ''
        return values

    def run(self):
        max_used_percent = self.get_threshold_var('max_used_percent', default=80.0, value_type='float')
        thresholds = {'max_used_percent': max_used_percent}
        stdout, error = self._run_command()
        if error:
            return error

        cpu_usages = self._parse_cpu_usage(stdout)
        if not cpu_usages:
            return self.fail('CPU 사용률 파싱 실패', message='show resource 출력에서 CPU Usage 값을 찾지 못했습니다.', stdout=stdout, thresholds=thresholds)

        max_item = max(cpu_usages, key=lambda item: item['used_percent'])
        over_threshold = [item for item in cpu_usages if item['used_percent'] > max_used_percent]
        metrics = {
            'cpu_usage_count': len(cpu_usages),
            'max_used_percent': max_item['used_percent'],
            'max_used_processor': max_item['processor'],
            'over_threshold': over_threshold,
            'cpu_usages': cpu_usages,
        }
        if over_threshold:
            return self.fail(error="CPU 임계치 초과", metrics=metrics, thresholds=thresholds, reasons='CPU Usage 값이 임계치를 초과했습니다.', message=f'CPU 사용률 최대값 {max_item["used_percent"]}%가 기준 {max_used_percent}%를 초과했습니다.')
        return self.ok(metrics=metrics, thresholds=thresholds, reasons='모든 CPU Usage 값이 임계치 이하입니다.', message=f'CPU 사용률 점검 정상: 최대 {max_item["used_percent"]}%, 기준 {max_used_percent}%.')


CHECK_CLASS = Check
