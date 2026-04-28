# type_name

일상점검(상태점검)

# area_name

서버

# category_name

MEMORY

# application_type

UNIX

# application

solaris

# inspection_code

SVR-2-3

# is_required

필수

# inspection_name

Paging Space

# inspection_content

가상 메모리(swap)의 전체 용량, 남은 용량, 장치별 분포를 기준으로 paging space 상태를 점검합니다.

# inspection_command

```bash
swap -l
```

# inspection_output

```text
swapfile           dev   swaplo   blocks    free
/dev/dsk/c0t0d0s1  118,1 16       1048576   524288
/dev/dsk/c0t0d0s2  118,2 16       2097152   1048576
```

# description

- `blocks`는 전체 스왑 용량, `free`는 사용 가능한 스왑 공간.
  - 일반적으로 물리 메모리의 1~2배 이상 스왑 구성을 권고.
  - `free`가 충분하지 않으면 메모리 부족 가능성을 점검해야 함.

# thresholds

[
    {id: null, key: "max_swap_used_percent", value: "80", sortOrder: 0}
,
{id: null, key: "min_swap_free_percent", value: "20", sortOrder: 1}
,
{id: null, key: "min_swap_device_count", value: "1", sortOrder: 2}
,
{id: null, key: "failure_keywords", value: "장치를 찾을 수 없습니다,not found,cannot,command not found,module missing", sortOrder: 3}
]

# inspection_script

# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


SWAP_LIST_COMMAND = 'swap -l'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def _parse_int(self, value):
        try:
            return int(str(value).strip())
        except (TypeError, ValueError):
            return None

    def _parse_swap_rows(self, text):
        lines = [line.rstrip() for line in (text or '').splitlines() if line.strip()]
        if not lines:
            return {
                'header_found': False,
                'rows': [],
            }

        header_found = False
        rows = []
        for index, line in enumerate(lines):
            columns = re.split(r'\s+', line.strip())
            lowered = [column.lower() for column in columns]
            if not header_found:
                if all(name in lowered for name in ('swapfile', 'blocks', 'free')):
                    header_found = True
                continue

            if len(columns) < 5:
                continue

            blocks = self._parse_int(columns[3])
            free_blocks = self._parse_int(columns[4])
            if blocks is None or free_blocks is None:
                continue

            used_blocks = max(blocks - free_blocks, 0)
            free_percent = round((free_blocks / blocks) * 100, 2) if blocks > 0 else 0.0
            used_percent = round((used_blocks / blocks) * 100, 2) if blocks > 0 else 100.0

            rows.append({
                'line_number': index + 1,
                'swapfile': columns[0],
                'device': columns[1],
                'swaplo': columns[2],
                'blocks': blocks,
                'free_blocks': free_blocks,
                'used_blocks': used_blocks,
                'free_percent': free_percent,
                'used_percent': used_percent,
            })

        return {
            'header_found': header_found,
            'rows': rows,
        }

    def _build_device_summary(self, rows, limit=3):
        if not rows:
            return '장치 요약 없음'

        summaries = []
        for row in rows[:limit]:
            summaries.append(
                f"{row['swapfile']} free {row['free_percent']:.2f}% ({row['free_blocks']}/{row['blocks']} blocks)"
            )
        if len(rows) > limit:
            summaries.append(f"외 {len(rows) - limit}개")
        return ', '.join(summaries)

    def run(self):
        max_swap_used_percent = self.get_threshold_var('max_swap_used_percent', default=80.0, value_type='float')
        min_swap_free_percent = self.get_threshold_var('min_swap_free_percent', default=20.0, value_type='float')
        min_swap_device_count = self.get_threshold_var('min_swap_device_count', default=1, value_type='int')
        failure_keywords_raw = self.get_threshold_var('failure_keywords', default='', value_type='str')

        rc, out, err = self._ssh(SWAP_LIST_COMMAND)

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
                    'Solaris Paging Space 점검에 실패했습니다. '
                    '현재 상태: swap -l 명령을 정상적으로 실행하지 못했습니다.'
                ),
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        command_error = self._detect_command_error(
            out,
            err,
            extra_patterns=['permission denied', 'not supported', 'unknown userland error'],
        )
        if command_error:
            return self.fail(
                '점검 명령 실행 실패',
                message=(
                    'Solaris Paging Space 점검에 실패했습니다. '
                    f'현재 상태: swap -l 출력에서 실행 오류가 확인되었습니다: {command_error}'
                ),
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        text = (out or '').strip()
        failure_keywords = [keyword.strip() for keyword in failure_keywords_raw.split(',') if keyword.strip()]
        combined_output = '\n'.join(part for part in (text, (err or '').strip()) if part)
        matched_failure_keywords = [
            keyword for keyword in failure_keywords
            if keyword.lower() in combined_output.lower()
        ]
        if matched_failure_keywords:
            return self.fail(
                'Paging Space 실패 키워드 감지',
                message=(
                    'Solaris Paging Space 점검에 실패했습니다. '
                    f'현재 상태: 출력에서 실패 키워드 {matched_failure_keywords}가 확인되었습니다.'
                ),
                stdout=text,
                stderr=(err or '').strip(),
            )

        parsed = self._parse_swap_rows(text)
        if not parsed['header_found']:
            return self.fail(
                'Paging Space 파싱 실패',
                message=(
                    'Solaris Paging Space 점검에 실패했습니다. '
                    '현재 상태: swap -l 출력에서 swapfile/blocks/free 헤더를 찾지 못했습니다.'
                ),
                stdout=text,
                stderr=(err or '').strip(),
            )

        rows = parsed['rows']
        if not rows:
            return self.fail(
                'Paging Space 파싱 실패',
                message=(
                    'Solaris Paging Space 점검에 실패했습니다. '
                    '현재 상태: swap -l 출력에서 swap 장치 정보를 해석하지 못했습니다.'
                ),
                stdout=text,
                stderr=(err or '').strip(),
            )

        invalid_rows = [
            row for row in rows
            if row['blocks'] <= 0 or row['free_blocks'] < 0 or row['free_blocks'] > row['blocks']
        ]
        if invalid_rows:
            invalid_summary = ', '.join(
                f"{row['swapfile']} free {row['free_blocks']} / blocks {row['blocks']}"
                for row in invalid_rows[:3]
            )
            return self.fail(
                'Paging Space 데이터 불일치',
                message=(
                    'Solaris Paging Space 점검에 실패했습니다. '
                    f'현재 상태: swap 장치 데이터가 비정상입니다: {invalid_summary}.'
                ),
                stdout=text,
                stderr=(err or '').strip(),
            )

        device_count = len(rows)
        total_blocks = sum(row['blocks'] for row in rows)
        total_free_blocks = sum(row['free_blocks'] for row in rows)
        total_used_blocks = sum(row['used_blocks'] for row in rows)
        used_percent = round((total_used_blocks / total_blocks) * 100, 2) if total_blocks else 100.0
        free_percent = round((total_free_blocks / total_blocks) * 100, 2) if total_blocks else 0.0
        device_summary = self._build_device_summary(rows)

        if total_blocks <= 0:
            return self.fail(
                'Paging Space 총량 이상',
                message=(
                    'Solaris Paging Space 점검에 실패했습니다. '
                    f'현재 상태: 전체 swap blocks가 {total_blocks}로 집계되어 정상적인 용량을 확인하지 못했습니다.'
                ),
                stdout=text,
                stderr=(err or '').strip(),
            )

        if device_count < min_swap_device_count:
            return self.fail(
                'swap 장치 수 부족',
                message=(
                    'Solaris Paging Space 점검에 실패했습니다. '
                    f'현재 상태: swap 장치 {device_count}개로 집계되어 기준 {min_swap_device_count}개 이상을 만족하지 못했습니다. '
                    f'장치 요약: {device_summary}.'
                ),
                stdout=text,
                stderr=(err or '').strip(),
            )

        if used_percent > max_swap_used_percent or free_percent < min_swap_free_percent:
            return self.fail(
                'Paging Space 사용률 임계치 초과',
                message=(
                    'Solaris Paging Space 점검에 실패했습니다. '
                    f'현재 상태: swap 사용률 {used_percent:.2f}% (기준 {max_swap_used_percent:.2f}% 이하), '
                    f'free {free_percent:.2f}% (기준 {min_swap_free_percent:.2f}% 이상), '
                    f'장치 {device_count}개, 전체 {total_blocks} blocks, 사용 {total_used_blocks} blocks, '
                    f'여유 {total_free_blocks} blocks, 장치 요약: {device_summary}.'
                ),
                stdout=text,
                stderr=(err or '').strip(),
            )

        return self.ok(
            metrics={
                'swap_device_count': device_count,
                'total_swap_blocks': total_blocks,
                'total_swap_used_blocks': total_used_blocks,
                'total_swap_free_blocks': total_free_blocks,
                'swap_used_percent': used_percent,
                'swap_free_percent': free_percent,
                'largest_swap_device': max(rows, key=lambda row: row['blocks'])['swapfile'],
                'largest_swap_blocks': max(row['blocks'] for row in rows),
                'lowest_device_free_percent': min(row['free_percent'] for row in rows),
                'device_rows': rows,
                'matched_failure_keywords': matched_failure_keywords,
            },
            thresholds={
                'max_swap_used_percent': max_swap_used_percent,
                'min_swap_free_percent': min_swap_free_percent,
                'min_swap_device_count': min_swap_device_count,
                'failure_keywords': failure_keywords,
            },
            reasons=(
                f'swap 장치 {device_count}개가 모두 정상 해석되었고 전체 사용률 {used_percent:.2f}%와 '
                f'free {free_percent:.2f}%가 기준 이내입니다.'
            ),
            message=(
                'Solaris Paging Space가 정상입니다. '
                f'현재 상태: swap 사용률 {used_percent:.2f}% (기준 {max_swap_used_percent:.2f}% 이하), '
                f'free {free_percent:.2f}% (기준 {min_swap_free_percent:.2f}% 이상), '
                f'장치 {device_count}개, 전체 {total_blocks} blocks, 사용 {total_used_blocks} blocks, '
                f'여유 {total_free_blocks} blocks, 장치 요약: {device_summary}.'
            ),
        )


CHECK_CLASS = Check
