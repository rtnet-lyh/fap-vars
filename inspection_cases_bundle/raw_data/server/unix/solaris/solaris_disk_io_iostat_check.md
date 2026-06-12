# type_name

일상점검(상태점검)

# area_name

서버

# category_name

DISK

# application_type

UNIX

# application

solaris

# inspection_code

SVR-3-5

# is_required

권고

# inspection_name

Disk I/O 점검

# inspection_content

Solaris 서버의 디스크별 I/O 대기, 서비스 시간, 바쁨률을 확인해 병목 가능성을 점검합니다.

# inspection_command

```bash
iostat -x
```

# inspection_output

```text
extended device statistics
device   r/s   w/s   kr/s   kw/s   wait actv svc_t  %w  %b
sd0     15.0  10.0  150.0  100.0   0.0  1.0  10.5   5  50
sd1      5.0   3.0   50.0   30.0   0.0  0.5   8.0   0  25
sd2      0.5   0.2    5.0    2.0   0.0  0.1   7.0   0  10
```

# description

- `svc_t`가 20ms 이상이면 성능 문제 가능성이 큼.
  - `%b`가 80% 이상이면 디스크가 과도하게 사용 중인 상태.
  - `wait`, `actv`, `r/s`, `w/s`를 함께 보고 병목 여부를 판단.

# thresholds

[
    {id: null, key: "max_service_time_ms", value: "20", sortOrder: 0}
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
    CONNECTION_METHOD = 'ssh'

    def _parse_float(self, value):
        try:
            return float(str(value).strip())
        except (TypeError, ValueError):
            return None

    def _parse_rows(self, text):
        lines = [line.rstrip() for line in (text or '').splitlines() if line.strip()]
        header_banner_found = False
        header_found = False
        rows = []

        for index, line in enumerate(lines):
            stripped = line.strip()
            lowered = stripped.lower()
            if lowered == 'extended device statistics':
                header_banner_found = True
                continue

            parts = re.split(r'\s+', stripped)
            part_headers = [part.lower() for part in parts]
            if 'device' in part_headers and 'svc_t' in part_headers and '%b' in part_headers:
                header_found = True
                continue

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
                'service_time_ms': parsed_values[6],
                'wait_percent': parsed_values[7],
                'busy_percent': parsed_values[8],
            })

        return {
            'header_banner_found': header_banner_found,
            'header_found': header_found,
            'rows': rows,
        }

    def _build_device_summary(self, rows, limit=3):
        if not rows:
            return '장치 요약 없음'

        summaries = []
        for row in rows[:limit]:
            summaries.append(
                f"{row['device']} svc_t {row['service_time_ms']:.2f}ms, %b {row['busy_percent']:.2f}%, "
                f"wait {row['wait']:.2f}, actv {row['active']:.2f}"
            )
        if len(rows) > limit:
            summaries.append(f"외 {len(rows) - limit}개")
        return ', '.join(summaries)

    def run(self):
        max_service_time_ms = self.get_threshold_var('max_service_time_ms', default=20, value_type='float')
        max_busy_percent = self.get_threshold_var('max_busy_percent', default=80, value_type='float')
        failure_keywords_raw = self.get_threshold_var('failure_keywords', default='', value_type='str')

        rc, out, err = self._ssh(IOSTAT_COMMAND)
        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'SSH 연결 확인에 실패했습니다.').strip(),
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

        failure_keywords = [keyword.strip() for keyword in failure_keywords_raw.split(',') if keyword.strip()]
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

        worst_svc = max(rows, key=lambda item: item['service_time_ms'])
        worst_busy = max(rows, key=lambda item: item['busy_percent'])
        highest_wait = max(rows, key=lambda item: item['wait'])
        highest_active = max(rows, key=lambda item: item['active'])
        device_summary = self._build_device_summary(sorted(rows, key=lambda item: (item['service_time_ms'], item['busy_percent']), reverse=True))

        if worst_svc['service_time_ms'] >= max_service_time_ms:
            return self.fail(
                'Disk I/O 서비스 시간 임계치 초과',
                message=(
                    'Solaris Disk I/O 점검에 실패했습니다. '
                    f'현재 상태: {worst_svc["device"]} svc_t {worst_svc["service_time_ms"]:.2f}ms '
                    f'(기준 {max_service_time_ms:.2f}ms 미만), %b {worst_svc["busy_percent"]:.2f}%, '
                    f'wait {worst_svc["wait"]:.2f}, actv {worst_svc["active"]:.2f}, '
                    f'r/s {worst_svc["read_per_sec"]:.2f}, w/s {worst_svc["write_per_sec"]:.2f}, 장치 요약: {device_summary}.'
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
                    f'(기준 {max_busy_percent:.2f}% 미만), svc_t {worst_busy["service_time_ms"]:.2f}ms, '
                    f'wait {worst_busy["wait"]:.2f}, actv {worst_busy["active"]:.2f}, '
                    f'r/s {worst_busy["read_per_sec"]:.2f}, w/s {worst_busy["write_per_sec"]:.2f}, 장치 요약: {device_summary}.'
                ),
                stdout=text,
                stderr=(err or '').strip(),
            )

        return self.ok(
            metrics={
                'device_count': len(rows),
                'worst_service_device': worst_svc['device'],
                'worst_service_time_ms': worst_svc['service_time_ms'],
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
                f'최대 svc_t는 {worst_svc["device"]} {worst_svc["service_time_ms"]:.2f}ms, '
                f'최대 %b는 {worst_busy["device"]} {worst_busy["busy_percent"]:.2f}%입니다.'
            ),
            message=(
                'Solaris Disk I/O가 정상입니다. '
                f'현재 상태: 디스크 {len(rows)}개, 최대 svc_t {worst_svc["device"]} {worst_svc["service_time_ms"]:.2f}ms '
                f'(기준 {max_service_time_ms:.2f}ms 미만), 최대 %b {worst_busy["device"]} {worst_busy["busy_percent"]:.2f}% '
                f'(기준 {max_busy_percent:.2f}% 미만), 최대 wait {highest_wait["device"]} {highest_wait["wait"]:.2f}, '
                f'최대 actv {highest_active["device"]} {highest_active["active"]:.2f}, 장치 요약: {device_summary}.'
            ),
        )


CHECK_CLASS = Check
