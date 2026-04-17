# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


LOG_CLUSTER_COMMAND = (
    "if(Get-WinEvent -ListLog 'Microsoft-Windows-FailoverClustering/Operational' -ErrorAction SilentlyContinue)"
    "{Get-WinEvent -FilterHashtable @{LogName='Microsoft-Windows-FailoverClustering/Operational'; StartTime=(Get-Date).AddDays(-30)} "
    "-ErrorAction SilentlyContinue | Where-Object { $_.Message -match '(?i)cluster|resource status|unknown|offline|online|error' } | "
    "Select-Object -First 100 TimeCreated,Id,LevelDisplayName,@{N='Message';E={($_.Message -replace '\\r?\\n',' ')}} | Format-Table -Wrap -Auto}"
    "else{'Failover Clustering log not present on this PC (Windows 11 is typically not a local WSFC node).'}"
)

EVENT_PATTERN = re.compile(
    r'^(?P<time>\d{4}-\d{2}-\d{2}\s+(?:오전|오후)\s+\d{1,2}:\d{2}:\d{2})\s+'
    r'(?P<id>\d+)\s+'
    r'(?P<level>오류|경고|정보|Error|Warning|Critical|Information)\s+'
    r'(?P<message>.+)$'
)


def _parse_int(value):
    return int(str(value).strip())


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'winrm'
    WINRM_SHELL = 'powershell'

    def run(self):
        max_cluster_event_count = self.get_threshold_var('max_cluster_event_count', default=0, value_type='int')
        failure_keywords_raw = self.get_threshold_var('failure_keywords', default='', value_type='str')

        rc, out, err = self._run_ps(LOG_CLUSTER_COMMAND)

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
                message='Windows 클러스터 로그 점검 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        text = (out or '').strip()
        if not text:
            return self.ok(
                metrics={
                    'cluster_log_present': False,
                    'cluster_event_count': 0,
                    'offline_event_count': 0,
                    'unknown_or_error_event_count': 0,
                    'online_event_count': 0,
                    'matched_failure_keywords': [],
                },
                thresholds={
                    'max_cluster_event_count': max_cluster_event_count,
                    'failure_keywords': [],
                },
                reasons='Failover Clustering 로그 채널이 없거나 최근 30일 내 점검 대상 이벤트가 확인되지 않았습니다.',
                message='Windows 클러스터 로그 점검이 정상 수행되었습니다.',
            )

        if 'Failover Clustering log not present on this PC (Windows 11 is typically not a local WSFC node).' in text:
            return self.ok(
                metrics={
                    'cluster_log_present': False,
                    'cluster_event_count': 0,
                    'offline_event_count': 0,
                    'unknown_or_error_event_count': 0,
                    'online_event_count': 0,
                    'matched_failure_keywords': [],
                },
                thresholds={
                    'max_cluster_event_count': max_cluster_event_count,
                    'failure_keywords': [],
                },
                reasons='Failover Clustering 로그 채널이 로컬 PC에 없으며, 이는 일반적인 Windows 11 환경에서 로컬 WSFC 노드가 아님을 의미할 수 있습니다.',
                message='Windows 클러스터 로그 점검이 정상 수행되었습니다.',
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
                '클러스터 로그 실패 키워드 감지',
                message='클러스터 로그 결과에서 실패 키워드가 확인되었습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        lines = [line.rstrip() for line in text.splitlines() if line.strip()]
        entries = []
        for line in lines:
            if line.startswith('TimeCreated') or line.startswith('-----------') or line.lstrip().startswith('---'):
                continue
            match = EVENT_PATTERN.match(line)
            if not match:
                continue
            entries.append({
                'time_created': match.group('time'),
                'event_id': _parse_int(match.group('id')),
                'level': match.group('level').strip(),
                'message': match.group('message').strip(),
            })

        if not entries:
            return self.fail(
                '클러스터 로그 파싱 실패',
                message='Failover Clustering 이벤트 항목을 해석하지 못했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        offline_entries = [
            entry for entry in entries
            if 'offline' in entry['message'].lower()
        ]
        online_entries = [
            entry for entry in entries
            if 'online' in entry['message'].lower()
        ]
        unknown_or_error_entries = [
            entry for entry in entries
            if 'unknown' in entry['message'].lower()
            or 'error' in entry['message'].lower()
            or entry['level'].lower() in ('critical', 'error', '오류')
        ]
        repeated_event_ids = {}
        for entry in entries:
            key = str(entry['event_id'])
            repeated_event_ids[key] = repeated_event_ids.get(key, 0) + 1
        repeated_events = [
            f"{key}({count})"
            for key, count in repeated_event_ids.items()
            if count > 1
        ]
        latest_entry = entries[0]

        if len(entries) > max_cluster_event_count:
            return self.fail(
                '클러스터 상태 이벤트 감지',
                message='최근 30일 내 클러스터 자원 또는 노드 상태 변경 이벤트가 기준치를 초과했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        return self.ok(
            metrics={
                'cluster_log_present': True,
                'cluster_event_count': len(entries),
                'offline_event_count': len(offline_entries),
                'unknown_or_error_event_count': len(unknown_or_error_entries),
                'online_event_count': len(online_entries),
                'latest_event_time': latest_entry['time_created'],
                'latest_event_id': latest_entry['event_id'],
                'repeated_events': repeated_events,
                'matched_failure_keywords': matched_failure_keywords,
            },
            thresholds={
                'max_cluster_event_count': max_cluster_event_count,
                'failure_keywords': failure_keywords,
            },
            reasons='최근 30일 내 클러스터 자원 또는 노드 상태 변경 이벤트 수가 기준 범위 내입니다.',
            message='Windows 클러스터 로그 점검이 정상 수행되었습니다.',
        )


CHECK_CLASS = Check
