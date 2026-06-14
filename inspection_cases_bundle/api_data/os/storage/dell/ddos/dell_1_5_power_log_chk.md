# type_name

일상점검

# area_name

storage

# category_name

상태점검

# application_type

dell

# application

ddos

# inspection_code

NETWORK-DELL-DDOS-DELL-1-5-POWER-LOG-CHK

# is_required

필수

# inspection_name

POWER 로그

# inspection_content

전원공급장치 오류 및 이상 유무 점검 (PS fail)

# inspection_command

```bash
alerts show current
```

# inspection_output

```text

```

# description

- 현재 시스템에 활성화된 Alert 및 Error 이벤트를 확인하는 명령어
- 시스템 운영 상태, 네트워크 장애, 서비스 오류, HW 이상 여부를 점검 가능
- Severity(ERROR/CRITICAL/WARNING) 기반으로 현재 장애 여부 확인 가능

- **양호**: 출력 결과의 Message에 `power_device_keywords`와 `power_status_keywords` 조건을 동시에 만족하는 관련 장애 메시지가 없는 경우
- **경고**: 출력 결과의 Message에 `power_device_keywords`와 `power_status_keywords` 조건을 동시에 만족하는 관련 장애 메시지가 있는 경우
- **확인 필요**: 명령어 수행 실패 또는 출력 결과를 확인할 수 없는 경우

# thresholds

[
    {id: null, key: "power_device_keywords", value: "power,psu,sps,voltage,power supply", sortOrder: 0}
,
{id: null, key: "power_status_keywords", value: "failed,fault,offline,error,critical", sortOrder: 1}
]

# inspection_script

# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


COMMAND_ERROR_MARKERS = ('syntax error', 'unknown command', 'invalid command', 'command not found')
COMMAND = 'alerts show current'
DEVICE_KEY = 'power_device_keywords'
STATUS_KEY = 'power_status_keywords'
DEFAULT_DEVICE_KEYWORDS = ['power', 'psu', 'sps', 'voltage', 'power supply']
DEFAULT_STATUS_KEYWORDS = ['failed', 'fault', 'offline', 'error', 'critical']
FAIL_ON_ANY_ALERT = False


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

    def _threshold_list(self, key, default_values):
        default_text = ','.join(default_values)
        return self._split_list(self.get_threshold_var(key, default=default_text, value_type='str'))

    def _normalize(self, value):
        return re.sub(r'[^a-z0-9]+', '', str(value or '').lower())

    def _contains_keyword(self, text, keyword):
        normalized_keyword = self._normalize(keyword)
        if not normalized_keyword:
            return False
        return normalized_keyword in self._normalize(text)

    def _parse_alerts(self, text, device_keywords, status_keywords):
        active_match = re.search(r'There\s+(?:is|are)\s+(\d+)\s+active alert', text, re.IGNORECASE)
        active_alert_count = int(active_match.group(1)) if active_match else 0
        bad_severity_lines = [line.strip() for line in text.splitlines() if re.search(r'\b(ERROR|CRITICAL)\b', line, re.IGNORECASE)]
        keyword_lines = []
        for line in text.splitlines():
            if any(self._contains_keyword(line, keyword) for keyword in device_keywords) and any(self._contains_keyword(line, keyword) for keyword in status_keywords):
                keyword_lines.append(line.strip())
        return {
            'active_alert_count': active_alert_count,
            'bad_severity_lines': bad_severity_lines,
            'keyword_matched_alert_lines': keyword_lines,
        }

    def run(self):
        device_keywords = self._threshold_list(DEVICE_KEY, DEFAULT_DEVICE_KEYWORDS)
        status_keywords = self._threshold_list(STATUS_KEY, DEFAULT_STATUS_KEYWORDS)
        thresholds = {DEVICE_KEY: device_keywords, STATUS_KEY: status_keywords}
        stdout, error = self._run_command()
        if error:
            return error

        metrics = self._parse_alerts(stdout, device_keywords, status_keywords)
        has_failure = bool(metrics['keyword_matched_alert_lines'])
        if FAIL_ON_ANY_ALERT:
            has_failure = has_failure or metrics['active_alert_count'] > 0 or bool(metrics['bad_severity_lines'])
        if has_failure:
            return self.fail('Alert 상태 기준 미달', message='Active Alert, ERROR/CRITICAL Severity 또는 장애 키워드가 확인되었습니다.', stdout=stdout, metrics=metrics, thresholds=thresholds)
        return self.ok(metrics=metrics, thresholds=thresholds, reasons='장애 Alert 조건이 확인되지 않았습니다.', message='Alert 상태 점검 정상.')


CHECK_CLASS = Check
