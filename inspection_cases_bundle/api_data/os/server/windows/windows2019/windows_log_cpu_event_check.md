# type_name

일상점검

# area_name

server

# category_name

상태점검

# application_type

windows

# application

windows2019

# inspection_code

W-REPLAY-CPU-LOG-01

# is_required

필수

# inspection_name

# inspection_content

CPU, WHEA, ECC, Machine Check와 관련된 최근 이벤트를 검색해 하드웨어 이상 징후를 확인합니다.

# inspection_command

```bash
$OutputEncoding = [System.Text.UTF8Encoding]::new($false); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); $e=Get-WinEvent -FilterHashtable @{LogName='System';StartTime=(Get-Date).AddDays(-30);Level=@(1,2,3)} -ErrorAction SilentlyContinue | Where-Object { $_.ProviderName -in @('Microsoft-Windows-WHEA-Logger','Microsoft-Windows-Kernel-Processor-Power') -or $_.Message -match '(?i)\bECC\b|uncorrectable|processor|cpu|offline' }; if($e){@($e | Select-Object TimeCreated,ProviderName,Id,LevelDisplayName,@{N='Message';E={($_.Message -replace '\r?\n',' ')}}) | ConvertTo-Json -Depth 4}else{'No CPU/ECC/offline-like events found in the last 30 days.'}
```

# inspection_output

```text
No CPU/ECC/offline-like events found in the last 30 days.
```

# description

- CPU 자체 오류뿐 아니라 WHEA 기반 하드웨어 교정 오류까지 포함해 확인합니다.
- 이벤트가 없거나 허용 범위 이내면 정상으로 봅니다.

- **정상**: CPU/ECC 관련 오류 또는 경고 이벤트 수가 기준 이내입니다.
- **경고**: CPU, WHEA, ECC 관련 이벤트 수가 임계치를 초과합니다.

# thresholds

[
    {id: null, key: "max_cpu_ecc_event_count", value: "0", sortOrder: 0}
,
{id: null, key: "failure_keywords", value: "", sortOrder: 1}
]

# inspection_script

# -*- coding: utf-8 -*-

import json

from .common._base import BaseCheck


LOG_CPU_COMMAND = (
    "$OutputEncoding = [System.Text.UTF8Encoding]::new($false); "
    "[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); "
    "$e=Get-WinEvent -FilterHashtable @{LogName='System';StartTime=(Get-Date).AddDays(-30);Level=@(1,2,3)} -ErrorAction SilentlyContinue | "
    "Where-Object { $_.ProviderName -in @('Microsoft-Windows-WHEA-Logger','Microsoft-Windows-Kernel-Processor-Power') -or $_.Message -match '(?i)\\bECC\\b|uncorrectable|processor|cpu|offline' }; "
    "if($e){@($e | Select-Object TimeCreated,ProviderName,Id,LevelDisplayName,@{N='Message';E={($_.Message -replace '\\r?\\n',' ')}}) | ConvertTo-Json -Depth 4}else{'No CPU/ECC/offline-like events found in the last 30 days.'}"
)


def _parse_int(value):
    return int(str(value).strip())


def _as_list(value):
    if isinstance(value, list):
        return value
    if value in (None, ''):
        return []
    return [value]


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'winrm'
    WINRM_SHELL = 'powershell'

    def run(self):
        max_cpu_ecc_event_count = self.get_threshold_var('max_cpu_ecc_event_count', default=0, value_type='int')
        failure_keywords_raw = self.get_threshold_var('failure_keywords', default='', value_type='str')

        rc, out, err = self._run_ps(LOG_CPU_COMMAND)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'WinRM 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if self._is_not_applicable(rc, err):
            return self.fail(
                'WinRM 실행 환경을 사용할 수 없습니다.',
                message='Windows CPU 로그 점검을 수행할 수 없습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='Windows CPU 로그 점검 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        text = (out or '').strip()
        if not text or 'No CPU/ECC/offline-like events found in the last 30 days.' in text:
            return self.ok(
                metrics={
                    'cpu_ecc_event_count': 0,
                    'ecc_event_count': 0,
                    'uncorrectable_event_count': 0,
                    'offline_event_count': 0,
                    'matched_failure_keywords': [],
                },
                thresholds={
                    'max_cpu_ecc_event_count': max_cpu_ecc_event_count,
                    'failure_keywords': [],
                },
                reasons='최근 30일 내 CPU/ECC/offline 관련 이벤트가 확인되지 않았습니다.',
                message=(
                    'Windows CPU 로그 점검이 정상입니다. '
                    '현재 상태: 최근 30일 내 CPU/ECC/offline 관련 이벤트가 없어 0건으로 집계했습니다.'
                ),
            )

        failure_keywords = [
            keyword.strip()
            for keyword in failure_keywords_raw.split(',')
            if keyword.strip()
        ]
        matched_failure_keywords = [
            keyword for keyword in failure_keywords if keyword.lower() in text.lower()
        ]
        if matched_failure_keywords:
            return self.fail(
                'CPU 로그 실패 키워드 감지',
                message='CPU 로그 결과에서 실패 키워드가 확인되었습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        try:
            raw_entries = json.loads(text)
        except json.JSONDecodeError:
            return self.fail(
                'CPU 로그 파싱 실패',
                message='CPU/ECC 관련 이벤트 JSON을 해석하지 못했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        entries = []
        for entry in _as_list(raw_entries):
            if not isinstance(entry, dict):
                continue
            event_id = entry.get('Id', '')
            entries.append({
                'time_created': str(entry.get('TimeCreated', '')).strip(),
                'provider_name': str(entry.get('ProviderName', '')).strip(),
                'event_id': _parse_int(event_id) if str(event_id).strip() else 0,
                'level': str(entry.get('LevelDisplayName', '')).strip(),
                'message': str(entry.get('Message', '')).strip(),
            })

        if not entries:
            return self.fail(
                'CPU 로그 파싱 실패',
                message='CPU/ECC 관련 이벤트 항목을 해석하지 못했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        ecc_entries = [entry for entry in entries if 'ecc' in entry['message'].lower()]
        uncorrectable_entries = [entry for entry in entries if 'uncorrectable' in entry['message'].lower()]
        offline_entries = [entry for entry in entries if 'offline' in entry['message'].lower()]
        latest_entry = entries[0]

        if len(entries) > max_cpu_ecc_event_count:
            return self.fail(
                'CPU/ECC 로그 이벤트 감지',
                message='최근 30일 내 CPU/ECC/offline 관련 이벤트가 기준치를 초과했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        return self.ok(
            metrics={
                'cpu_ecc_event_count': len(entries),
                'ecc_event_count': len(ecc_entries),
                'uncorrectable_event_count': len(uncorrectable_entries),
                'offline_event_count': len(offline_entries),
                'latest_event_time': latest_entry['time_created'],
                'latest_event_provider': latest_entry['provider_name'],
                'latest_event_id': latest_entry['event_id'],
                'matched_failure_keywords': matched_failure_keywords,
            },
            thresholds={
                'max_cpu_ecc_event_count': max_cpu_ecc_event_count,
                'failure_keywords': failure_keywords,
            },
            reasons='최근 30일 내 CPU/ECC/offline 관련 이벤트 수가 기준 범위 내입니다.',
            message=(
                f'Windows CPU 로그 점검이 정상입니다. 현재 상태: '
                f'이벤트 {len(entries)}건 (기준 {max_cpu_ecc_event_count}건 이하), '
                f'ECC {len(ecc_entries)}건, Uncorrectable {len(uncorrectable_entries)}건, '
                f'Offline {len(offline_entries)}건, 최신 이벤트 ID {latest_entry["event_id"]}.'
            ),
        )


CHECK_CLASS = Check
