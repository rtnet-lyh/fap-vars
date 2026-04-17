# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


LOG_CPU_COMMAND = (
    "$e=Get-WinEvent -FilterHashtable @{LogName='System';StartTime=(Get-Date).AddDays(-30);Level=@(1,2,3)} -ErrorAction SilentlyContinue | "
    "Where-Object { $_.ProviderName -in @('Microsoft-Windows-WHEA-Logger','Microsoft-Windows-Kernel-Processor-Power') -or $_.Message -match '(?i)\\bECC\\b|uncorrectable|processor|cpu|offline' }; "
    "if($e){$e | Select-Object TimeCreated,ProviderName,Id,LevelDisplayName,@{N='Message';E={($_.Message -replace '\\r?\\n',' ')}} | Format-Table -Wrap -Auto}else{'No CPU/ECC/offline-like events found in the last 30 days.'}"
)


def _parse_int(value):
    return int(str(value).strip())


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
            return self.not_applicable(
                'WinRM 실행 환경을 사용할 수 없습니다.',
                raw_output=(err or '').strip(),
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
                message='Windows CPU 로그 점검이 정상 수행되었습니다.',
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

        lines = [line.rstrip() for line in text.splitlines() if line.strip()]
        entries = []
        entry_pattern = re.compile(
            r'^(?P<time>\d{4}-\d{2}-\d{2}\s+(?:오전|오후)\s+\d{1,2}:\d{2}:\d{2})\s+'
            r'(?P<provider>.+?)\s+'
            r'(?P<id>\d+)\s+'
            r'(?P<level>오류|경고|정보|Error|Warning|Critical|Information)\s+'
            r'(?P<message>.+)$'
        )
        for line in lines:
            if line.startswith('TimeCreated') or line.startswith('-----------') or line.lstrip().startswith('---'):
                continue
            match = entry_pattern.match(line)
            if not match:
                continue
            entries.append({
                'time_created': match.group('time'),
                'provider_name': match.group('provider').strip(),
                'event_id': _parse_int(match.group('id')),
                'level': match.group('level').strip(),
                'message': match.group('message').strip(),
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
            message='Windows CPU 로그 점검이 정상 수행되었습니다.',
        )


CHECK_CLASS = Check
