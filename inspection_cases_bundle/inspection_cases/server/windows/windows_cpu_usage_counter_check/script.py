# -*- coding: utf-8 -*-

import csv
import io

from .common._base import BaseCheck


TYPEPERF_COMMAND = (
    "$OutputEncoding = [System.Text.UTF8Encoding]::new($false); "
    "[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); "
    'typeperf "\\Processor(_Total)\\% User Time" '
    '"\\Processor(_Total)\\% Privileged Time" '
    '"\\Processor(_Total)\\% Idle Time" '
    '"\\Processor(_Total)\\% Interrupt Time" -sc 3 -si 1'
)


def _parse_percent(value):
    return round(float(value), 2)


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'winrm'
    WINRM_SHELL = 'powershell'

    def run(self):
        max_usr_sys_percent = self.get_threshold_var('max_usr_sys_percent', default=80.0, value_type='float')
        min_idle_percent = self.get_threshold_var('min_idle_percent', default=20.0, value_type='float')
        max_interrupt_percent = self.get_threshold_var('max_interrupt_percent', default=5.0, value_type='float')
        failure_keywords_raw = self.get_threshold_var('failure_keywords', default='', value_type='str')

        rc, out, err = self._run_ps(TYPEPERF_COMMAND)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'WinRM 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if self._is_not_applicable(rc, err):
            return self.fail(
                'WinRM 실행 환경을 사용할 수 없습니다.',
                message='Windows CPU 사용률 점검을 수행할 수 없습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='Windows CPU 사용률 점검 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        text = (out or '').strip()
        if not text:
            return self.fail(
                'CPU 사용률 정보 없음',
                message='typeperf 결과가 비어 있습니다.',
                stdout='',
                stderr=(err or '').strip(),
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
                'CPU 점검 실패 키워드 감지',
                message='typeperf 결과에서 실패 키워드가 확인되었습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        try:
            rows = list(csv.reader(io.StringIO(text)))
        except csv.Error:
            rows = []

        if len(rows) < 2:
            return self.fail(
                'CPU 통계 파싱 실패',
                message='typeperf CSV 결과를 해석하지 못했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        header = rows[0]
        if len(header) < 5:
            return self.fail(
                'CPU 통계 헤더 파싱 실패',
                message='typeperf 헤더 컬럼 수가 올바르지 않습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        expected_columns = [
            '% User Time',
            '% Privileged Time',
            '% Idle Time',
            '% Interrupt Time',
        ]
        for index, expected in enumerate(expected_columns, start=1):
            if expected not in header[index]:
                return self.fail(
                    'CPU 통계 헤더 파싱 실패',
                    message='typeperf 헤더 형식이 예상과 다릅니다.',
                    stdout=text,
                    stderr=(err or '').strip(),
                )

        sample_rows = []
        for row in rows[1:]:
            if len(row) < 5:
                continue

            try:
                user_percent = _parse_percent(row[1])
                privileged_percent = _parse_percent(row[2])
                idle_percent = _parse_percent(row[3])
                interrupt_percent = _parse_percent(row[4])
            except ValueError:
                continue

            sample_rows.append({
                'timestamp': row[0],
                'user_percent': user_percent,
                'privileged_percent': privileged_percent,
                'usr_sys_percent': round(user_percent + privileged_percent, 2),
                'idle_percent': idle_percent,
                'interrupt_percent': interrupt_percent,
            })

        if not sample_rows:
            return self.fail(
                'CPU 통계 파싱 실패',
                message='typeperf 결과에서 CPU 사용률 데이터를 해석하지 못했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        sample_count = len(sample_rows)
        avg_user_percent = round(sum(row['user_percent'] for row in sample_rows) / sample_count, 2)
        avg_privileged_percent = round(sum(row['privileged_percent'] for row in sample_rows) / sample_count, 2)
        avg_usr_sys_percent = round(sum(row['usr_sys_percent'] for row in sample_rows) / sample_count, 2)
        avg_idle_percent = round(sum(row['idle_percent'] for row in sample_rows) / sample_count, 2)
        avg_interrupt_percent = round(sum(row['interrupt_percent'] for row in sample_rows) / sample_count, 2)

        peak_usr_sys_sample = max(sample_rows, key=lambda row: row['usr_sys_percent'])
        peak_interrupt_sample = max(sample_rows, key=lambda row: row['interrupt_percent'])

        if avg_usr_sys_percent >= max_usr_sys_percent:
            return self.fail(
                'CPU 사용률 임계치 초과',
                message='사용자+시스템 CPU 사용률 평균이 기준치를 초과했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        if avg_idle_percent < min_idle_percent:
            return self.fail(
                'CPU 유휴율 임계치 미달',
                message='CPU idle 비율 평균이 기준치 미만입니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        if avg_interrupt_percent >= max_interrupt_percent:
            return self.fail(
                'CPU 인터럽트 처리 비율 임계치 초과',
                message='Interrupt Time 평균이 기준치를 초과했습니다.',
                stdout=text,
                stderr=(err or '').strip(),
            )

        host_name = header[1].lstrip('\\').split('\\', 1)[0] if header[1] else ''

        return self.ok(
            metrics={
                'sample_count': sample_count,
                'host_name': host_name,
                'avg_user_percent': avg_user_percent,
                'avg_privileged_percent': avg_privileged_percent,
                'avg_usr_sys_percent': avg_usr_sys_percent,
                'avg_idle_percent': avg_idle_percent,
                'avg_interrupt_percent': avg_interrupt_percent,
                'max_usr_sys_percent': peak_usr_sys_sample['usr_sys_percent'],
                'max_usr_sys_timestamp': peak_usr_sys_sample['timestamp'],
                'max_interrupt_percent': peak_interrupt_sample['interrupt_percent'],
                'max_interrupt_timestamp': peak_interrupt_sample['timestamp'],
                'matched_failure_keywords': matched_failure_keywords,
            },
            thresholds={
                'max_usr_sys_percent': max_usr_sys_percent,
                'min_idle_percent': min_idle_percent,
                'max_interrupt_percent': max_interrupt_percent,
                'failure_keywords': failure_keywords,
            },
            reasons='Windows CPU 사용률 평균, 유휴율 평균, 인터럽트 처리 시간 평균이 모두 기준 범위 내입니다.',
            message=(
                f'Windows CPU 사용률 점검이 정상입니다. 현재 상태: '
                f'host={host_name or "unknown"}, User {avg_user_percent:.2f}%, '
                f'Privileged {avg_privileged_percent:.2f}%, User+System {avg_usr_sys_percent:.2f}% '
                f'(기준 {max_usr_sys_percent:.2f}% 이하), Idle {avg_idle_percent:.2f}% '
                f'(기준 {min_idle_percent:.2f}% 이상), Interrupt {avg_interrupt_percent:.2f}% '
                f'(기준 {max_interrupt_percent:.2f}% 이하).'
            ),
        )


CHECK_CLASS = Check
