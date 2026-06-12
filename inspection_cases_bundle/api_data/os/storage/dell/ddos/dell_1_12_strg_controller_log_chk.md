# type_name

일상점검

# area_name

상태점검

# category_name

storage

# application_type

dell

# application

ddos

# inspection_code

NETWORK-DELL-DDOS-DELL-1-12-STRG-CONTROLLER-LOG-CHK

# is_required

필수

# inspection_name

컨트롤러 상태 점검

# inspection_content

스토리지 디렉터(컨트롤러) Fault 여부

# inspection_command

```bash
system show hardware
```

# inspection_output

```text

```

# description

- system show hardware 명령어를 통해 스토리지 컨트롤러(Fibre Channel, SAS, NVRAM) 장착 및 인식 상태를 확인할 수 있음
- 컨트롤러 장치(Device) 및 Port 정보가 정상 표시되는지 점검 필요

- **양호**: 출력 결과에서 `controller_device_keywords` 관련 장치(Device) 및 Port 정보가 정상 표시될 경우
- **경고**: 출력 결과에서 `controller_device_keywords` 관련 장치(Device) 또는 Port 정보가 정상 표시되지 않거나 비정상 상태일 경우
- **확인 필요**: 명령어 수행 실패 또는 출력 결과를 확인할 수 없는 경우

# thresholds

[
    {id: null, key: "controller_device_keywords", value: "fibre channel,sas,nvram", sortOrder: 0}
]

# inspection_script

# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


COMMAND_ERROR_MARKERS = ('syntax error', 'unknown command', 'invalid command', 'command not found')
COMMAND = 'system show hardware'
KEYWORD_KEY = 'controller_device_keywords'
DEFAULT_KEYWORDS = ['fibre channel', 'sas', 'nvram']


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'generic_network'
    PARAMIKO_REUSE_SESSION = True

    def _detect_cli_error(self, *texts):
        for text in texts:
            for line in str(text or '').splitlines():
                stripped = line.strip()
                lowered = stripped.lower()
                if stripped and any(marker in lowered for marker in COMMAND_ERROR_MARKERS):
                    return stripped
        return ''

    def _run_command(self):
        results = self._run_paramiko_commands([COMMAND], profile=self.PARAMIKO_PROFILE)
        if not results:
            return None, self.fail('점검 명령 실행 실패', message='Paramiko 명령 실행 결과가 비어 있습니다.')
        result = results[0]
        stdout = (result.get('stdout') or '').strip()
        stderr = (result.get('stderr') or '').strip()
        if result.get('rc') != 0:
            return None, self.fail('점검 명령 실행 실패', message=f'{COMMAND} 명령 실행에 실패했습니다.', stdout=stdout, stderr=stderr)
        error_text = self._detect_cli_error(stdout, stderr)
        if error_text:
            return None, self.fail('점검 명령 실행 실패', message=f'{COMMAND} 명령 출력에서 오류가 확인되었습니다: {error_text}', stdout=stdout, stderr=stderr)
        return stdout, None

    def _split_list(self, value):
        return [item.strip() for item in re.split(r'[,|\n]+', str(value or '')) if item.strip()]

    def _threshold_keywords(self):
        return self._split_list(self.get_threshold_var(KEYWORD_KEY, default=','.join(DEFAULT_KEYWORDS), value_type='str'))

    def _normalize(self, value):
        return re.sub(r'[^a-z0-9]+', '', str(value or '').lower())

    def _contains_keyword(self, text, keyword):
        normalized_keyword = self._normalize(keyword)
        if not normalized_keyword:
            return False
        if normalized_keyword == 'fc':
            lowered = str(text or '').lower()
            return 'fibrechannel' in self._normalize(text) or 'gbfc' in self._normalize(text) or re.search(r'\bfc\b', lowered) is not None
        return normalized_keyword in self._normalize(text)

    def _parse_hardware_rows(self, text):
        rows = []
        for line in text.splitlines():
            stripped = line.rstrip()
            if not stripped or stripped.startswith('Slot') or set(stripped.strip()) <= {'-'}:
                continue
            parts = re.split(r'\s{2,}', stripped.strip())
            if len(parts) < 3:
                continue
            slot, vendor, device = parts[:3]
            if slot.lower() in ('slot', '----') or vendor.lower() == 'vendor':
                continue
            rows.append({'slot': slot, 'vendor': vendor, 'device': device, 'ports': parts[3] if len(parts) >= 4 else ''})
        return rows

    def _valid_ports(self, value):
        text = str(value or '').strip()
        return bool(text and text.lower() != '(empty)')

    def run(self):
        keywords = self._threshold_keywords()
        thresholds = {KEYWORD_KEY: keywords}
        stdout, error = self._run_command()
        if error:
            return error

        rows = self._parse_hardware_rows(stdout)
        matching = [row for row in rows if any(self._contains_keyword(row['device'], keyword) for keyword in keywords)]
        rows_with_ports = [row for row in matching if self._valid_ports(row.get('ports'))]
        metrics = {
            'hardware_row_count': len(rows),
            'matching_device_count': len(matching),
            'matching_devices_with_ports_count': len(rows_with_ports),
            'matching_devices': matching,
        }
        if not matching or not rows_with_ports:
            return self.fail('하드웨어 상태 기준 미달', message='필수 장치 또는 포트 정보가 확인되지 않았습니다.', stdout=stdout, metrics=metrics, thresholds=thresholds)
        return self.ok(metrics=metrics, thresholds=thresholds, reasons='필수 장치와 포트 정보가 확인되었습니다.', message='하드웨어 상태 점검 정상.')


CHECK_CLASS = Check
