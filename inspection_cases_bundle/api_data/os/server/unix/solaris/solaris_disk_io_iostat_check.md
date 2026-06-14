# type_name

일상점검

# area_name

server

# category_name

상태점검

# application_type

unix

# application

solaris

# inspection_code

SOL-REPLAY-DISK-05

# is_required

# inspection_name

# inspection_content

# inspection_command

```bash

```

# inspection_output

```text

```

# description

# thresholds

[
    {id: null, key: "max_service_time_ms", value: "1000", sortOrder: 0}
,
{id: null, key: "max_busy_percent", value: "80", sortOrder: 1}
,
{id: null, key: "failure_keywords", value: "장치를 찾을 수 없습니다,not found,cannot,command not found,module missing", sortOrder: 2}
]

# inspection_script

# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


IOSTAT_COMMAND = 'iostat -x'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'paramiko'
    PARAMIKO_PROFILE = 'solaris'
    PARAMIKO_REUSE_SESSION = False

    def _parse_float(self, value):
        try:
            return float(str(value).strip())
        except (TypeError, ValueError):
            return None

    def _parse_rows(self, text):
        lines = [line.rstrip() for line in (text or '').splitlines() if line.strip()]
        header_banner_found = False
        header_found = False
        header_type = 'unknown'
        rows = []

        for index, line in enumerate(lines):
            stripped = line.strip()
            lowered = stripped.lower()
            if lowered == 'extended device statistics':
                header_banner_found = True
                continue

            parts = re.split(r'\s+', stripped)
            part_headers = [part.lower() for part in parts]
            
            if 'device' in part_headers and 'asvc_t' in part_headers and '%b' in part_headers:                
                header_found = True
                header_type = 'A'
                continue

            if 'device' in part_headers and 'svc_t' in part_headers and '%b' in part_headers:                
                header_found = True
                header_type = 'B'
                continue

            if header_found and header_type == 'A':
                if len(parts) != 11:
                    continue

                parsed_values = [self._parse_float(value) for value in parts[1:]]
                if any(value is None for value in parsed_values):
                    continue

                rows.append({
                    'line_number': index + 1,
                    'device': parts[0],
                    'read_per_sec': parsed_values[0],
                    'write_per_sec': parsed_values[1],
                    'read_kb_per_sec': parsed_values[2],
                    'write_kb_per_sec': parsed_values[3],
                    'wait': parsed_values[4],
                    'active': parsed_values[5],
                    'wait_service_time_ms': parsed_values[6],
                    'active_service_time_ms': parsed_values[7],
                    'wait_percent': parsed_values[8],
                    'busy_percent': parsed_values[9],
                })

            if header_found and header_type == 'B':
                if len(parts) != 10:
                    continue

                parsed_values = [self._parse_float(value) for value in parts[1:]]
                if any(value is None for value in parsed_values):
                    continue

                rows.append({
                    'line_number': index + 1,
                    'device': parts[0],
                    'read_per_sec': parsed_values[0],
                    'write_per_sec': parsed_values[1],
                    'read_kb_per_sec': parsed_values[2],
                    'write_kb_per_sec': parsed_values[3],
                    'wait': parsed_values[4],
                    'active': parsed_values[5],
                    'wait_service_time_ms': parsed_values[6],
                    'active_service_time_ms': parsed_values[6],
                    'wait_percent': parsed_values[7],
                    'busy_percent': parsed_values[8],
                })

        return {
            'header_banner_found': header_banner_found,
            'header_found': header_found,
            'rows': rows,
        }    

    def _split_keywords(self, raw_value):
        return [keyword.strip() for keyword in str(raw_value or '').split(',') if keyword.strip()]

    def _find_iostat_result(self, results):
        for item in reversed(results or []):
            if item.get('command') == IOSTAT_COMMAND:
                return item
        return None

    def run(self):
        max_service_time_ms = self.get_threshold_var('max_service_time_ms', default=1000, value_type='float')
        max_busy_percent = self.get_threshold_var('max_busy_percent', default=80, value_type='float')
        failure_keywords = self._split_keywords(
            self.get_threshold_var('failure_keywords', default='장치를 찾을 수 없습니다,not found,cannot,command not found,module missing', value_type='str')
        )

        try:
            results = self._run_solaris_commands([
                {'command': IOSTAT_COMMAND, 'timeout': 20},
            ])
        except ValueError as exc:
            return self.fail('권한 상승 설정 오류', message=str(exc))

        result = self._find_iostat_result(results)
        if result is None:
            failed_result = next((item for item in results if item.get('rc') != 0), None)
            rc = failed_result.get('rc') if failed_result else 1
            err = failed_result.get('stderr') if failed_result else ''
            if self._is_connection_error(rc, err):
                return self.fail(
                    '호스트 연결 실패',
                    message=(err or 'Paramiko 연결 확인에 실패했습니다.').strip(),
                    stderr=(err or '').strip(),
                )
            return self.fail(
                '점검 결과 없음',
                message='iostat -x 명령 실행 결과를 찾지 못했습니다.',
                stdout=(failed_result.get('stdout') or '').strip() if failed_result else '',
                stderr=(err or '').strip(),
            )

        rc = result.get('rc')
        out = result.get('stdout', '')
        err = result.get('stderr', '')
        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'Paramiko 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )
        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message=(
                    'Solaris Disk I/O 점검에 실패했습니다. '
                    '현재 상태: iostat -x 명령을 정상적으로 실행하지 못했습니다.'
                ),
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        text = (out or '').strip()
        command_error = self._detect_command_error(
            out,
            err,
            extra_patterns=['permission denied', 'not supported', 'unknown userland error'],
        )
        if command_error:
            return self.fail(
                '점검 명령 실행 실패',
                message=(
                    'Solaris Disk I/O 점검에 실패했습니다. '
                    f'현재 상태: iostat -x 출력에서 실행 오류가 확인되었습니다: {command_error}'
                ),
                stdout=text,
                stderr=(err or '').strip(),
            )

        combined_output = '\n'.join(part for part in (text, (err or '').strip()) if part)
        matched_failure_keywords = [
            keyword for keyword in failure_keywords
            if keyword.lower() in combined_output.lower()
        ]
        if matched_failure_keywords:
            return self.fail(
                'Disk I/O 실패 키워드 감지',
                message=(
                    'Solaris Disk I/O 점검에 실패했습니다. '
                    f'현재 상태: 출력에서 실패 키워드 {matched_failure_keywords}가 확인되었습니다.'
                ),
                stdout=text,
                stderr=(err or '').strip(),
            )

        parsed = self._parse_rows(text)
        if not parsed['header_banner_found']:
            return self.fail(
                'Disk I/O 파싱 실패',
                message=(
                    'Solaris Disk I/O 점검에 실패했습니다. '
                    '현재 상태: iostat -x 출력에서 extended device statistics 헤더를 찾지 못했습니다.'
                ),
                stdout=text,
                stderr=(err or '').strip(),
            )
        if not parsed['header_found']:
            return self.fail(
                'Disk I/O 파싱 실패',
                message=(
                    'Solaris Disk I/O 점검에 실패했습니다. '
                    '현재 상태: iostat -x 출력에서 device/svc_t/%b 헤더를 찾지 못했습니다.'
                ),
                stdout=text,
                stderr=(err or '').strip(),
            )

        rows = parsed['rows']
        if not rows:
            return self.fail(
                'Disk I/O 파싱 실패',
                message=(
                    'Solaris Disk I/O 점검에 실패했습니다. '
                    '현재 상태: iostat -x 출력에서 디스크 통계 정보를 해석하지 못했습니다.'
                ),
                stdout=text,
                stderr=(err or '').strip(),
            )

        worst_wait_svc = max(rows, key=lambda item: item['wait_service_time_ms'])
        worst_active_svc = max(rows, key=lambda item: item['active_service_time_ms'])

        worst_busy = max(rows, key=lambda item: item['busy_percent'])
        highest_wait = max(rows, key=lambda item: item['wait'])
        highest_active = max(rows, key=lambda item: item['active'])        
        
        if worst_wait_svc['wait_service_time_ms'] >= max_service_time_ms:
            return self.fail(
                'Disk I/O 서비스 시간 임계치 초과',
                message=(
                    'Solaris Disk I/O 점검에 실패했습니다. '
                    f'현재 상태: {worst_wait_svc["device"]} svc_t {worst_wait_svc["wait_service_time_ms"]:.2f}ms '
                    f'(기준 {max_service_time_ms:.2f}ms 미만), %b {worst_wait_svc["busy_percent"]:.2f}%, '
                    f'wait {worst_wait_svc["wait"]:.2f}, actv {worst_wait_svc["active"]:.2f}, '
                    f'r/s {worst_wait_svc["read_per_sec"]:.2f}, w/s {worst_wait_svc["write_per_sec"]:.2f}.'
                ),
                stdout=text,
                stderr=(err or '').strip(),
            )

        if worst_active_svc['active_service_time_ms'] >= max_service_time_ms:
            return self.fail(
                'Disk I/O 서비스 시간 임계치 초과',
                message=(
                    'Solaris Disk I/O 점검에 실패했습니다. '
                    f'현재 상태: {worst_active_svc["device"]} svc_t {worst_active_svc["service_time_ms"]:.2f}ms '
                    f'(기준 {max_service_time_ms:.2f}ms 미만), %b {worst_active_svc["busy_percent"]:.2f}%, '
                    f'wait {worst_active_svc["wait"]:.2f}, actv {worst_active_svc["active"]:.2f}, '
                    f'r/s {worst_active_svc["read_per_sec"]:.2f}, w/s {worst_active_svc["write_per_sec"]:.2f}.'
                ),
                stdout=text,
                stderr=(err or '').strip(),
            )

        if worst_busy['busy_percent'] >= max_busy_percent:
            return self.fail(
                'Disk I/O 바쁨률 임계치 초과',
                message=(
                    'Solaris Disk I/O 점검에 실패했습니다. '
                    f'현재 상태: {worst_busy["device"]} %b {worst_busy["busy_percent"]:.2f}% '
                    f'(기준 {max_busy_percent:.2f}% 미만), svc_t {worst_busy["wait_service_time_ms"]:.2f}ms, '
                    f'wait {worst_busy["wait"]:.2f}, actv {worst_busy["active"]:.2f}, '
                    f'r/s {worst_busy["read_per_sec"]:.2f}, w/s {worst_busy["write_per_sec"]:.2f}.'
                ),
                stdout=text,
                stderr=(err or '').strip(),
            )

        return self.ok(
            metrics={
                'device_count': len(rows),
                'worst_wait_service_device': worst_wait_svc['device'],
                'worst_wait_service_time_ms': worst_wait_svc['wait_service_time_ms'],
                'worst_active_service_device': worst_active_svc['device'],
                'worst_active_service_time_ms': worst_active_svc['active_service_time_ms'],
                'worst_busy_device': worst_busy['device'],
                'worst_busy_percent': worst_busy['busy_percent'],
                'highest_wait_device': highest_wait['device'],
                'highest_wait_value': highest_wait['wait'],
                'highest_active_device': highest_active['device'],
                'highest_active_value': highest_active['active'],
                'rows': rows,
                'matched_failure_keywords': matched_failure_keywords,
            },
            thresholds={
                'max_service_time_ms': max_service_time_ms,
                'max_busy_percent': max_busy_percent,
                'failure_keywords': failure_keywords,
            },
            reasons=(
                f'모든 디스크의 svc_t와 %b가 기준 이내입니다. '
                f'최대 wsvc_t는 {worst_wait_svc["device"]} {worst_wait_svc["wait_service_time_ms"]:.2f}ms, '
                f'최대 asvc_t는 {worst_active_svc["device"]} {worst_active_svc["active_service_time_ms"]:.2f}ms, '
                f'최대 %b는 {worst_busy["device"]} {worst_busy["busy_percent"]:.2f}%입니다.'
            ),
            message=(
                'Solaris Disk I/O가 정상입니다. '
                f'현재 상태: 디스크 {len(rows)}개, 최대 wsvc_t {worst_wait_svc["device"]} {worst_wait_svc["wait_service_time_ms"]:.2f}ms '
                f'현재 상태: 디스크 {len(rows)}개, 최대 asvc_t {worst_active_svc["device"]} {worst_active_svc["active_service_time_ms"]:.2f}ms '
                f'(기준 {max_service_time_ms:.2f}ms 미만), 최대 %b {worst_busy["device"]} {worst_busy["busy_percent"]:.2f}% '
                f'(기준 {max_busy_percent:.2f}% 미만), 최대 wait {highest_wait["device"]} {highest_wait["wait"]:.2f}, '
                f'최대 actv {highest_active["device"]} {highest_active["active"]:.2f}.'
            ),
        )


CHECK_CLASS = Check
