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

SVR-2-1

# is_required

필수

# inspection_name

메모리 사용률

# inspection_content

가용 메모리와 페이지 입출력 수치를 기반으로 메모리 압박 여부를 점검합니다.

# inspection_command

```bash
vmstat
```

# inspection_output

```text
kthr      memory            page            disk          faults      cpu
r b   swap  free   re mf pi po fr sr  in  sy  cs us sy id
1 0   1024  2048   0  0  0  0  0  0   10  20  30  5  3 92
```

# description

- `free`는 사용 가능한 물리 메모리이며, 총 메모리의 약 20% 이상을 권장.
  - `swap`, `pi`, `po` 증가는 메모리 압박 신호로 볼 수 있음.
  - `us`, `sy`, `id`를 함께 확인해 CPU와 메모리 병목을 같이 판단.

# thresholds

[
    {id: null, key: "min_free_kb", value: "1024", sortOrder: 0}
,
{id: null, key: "max_page_in_count", value: "0", sortOrder: 1}
,
{id: null, key: "max_page_out_count", value: "0", sortOrder: 2}
,
{id: null, key: "failure_keywords", value: "장치를 찾을 수 없습니다,not found,module,cannot,command not found", sortOrder: 3}
]

# inspection_script

# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


VMSTAT_COMMAND = 'vmstat'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def _split_keywords(self, raw_value):
        return [token.strip() for token in str(raw_value or '').split(',') if token.strip()]

    def _to_int(self, value):
        try:
            return int(str(value).strip())
        except (TypeError, ValueError):
            return None

    def _to_float(self, value):
        try:
            return float(str(value).strip())
        except (TypeError, ValueError):
            return None

    def _parse_vmstat_row(self, text):
        lines = [line.strip() for line in (text or '').splitlines() if line.strip()]
        if len(lines) < 3:
            return None

        header_line = None
        value_line = None
        for index, line in enumerate(lines):
            if re.search(r'(^|\s)swap\s+free\s+re\s+mf\s+pi\s+po', line):
                if index + 1 < len(lines):
                    header_line = line
                    value_line = lines[index + 1]
                    break

        if not header_line or not value_line:
            return None

        headers = re.split(r'\s+', header_line)
        values = re.split(r'\s+', value_line)
        if len(headers) != len(values):
            return None

        row = {}
        for idx, header in enumerate(headers):
            key = header.lower()
            if key == 'sy':
                key = 'system_calls' if 'system_calls' not in row else 'system_percent'
            row[key] = values[idx]

        return row

    def run(self):
        min_free_kb = self.get_threshold_var('min_free_kb', default=1024, value_type='int')
        max_page_in_count = self.get_threshold_var('max_page_in_count', default=0, value_type='int')
        max_page_out_count = self.get_threshold_var('max_page_out_count', default=0, value_type='int')
        failure_keywords = self._split_keywords(
            self.get_threshold_var(
                'failure_keywords',
                default='장치를 찾을 수 없습니다,not found,module,cannot,command not found',
                value_type='str',
            )
        )

        rc, out, err = self._ssh(VMSTAT_COMMAND)
        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'SSH 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )
        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='Solaris 메모리 사용률 점검에 실패했습니다. 현재 상태: vmstat 명령을 정상적으로 실행하지 못했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )
        command_error = self._detect_command_error(
            out,
            err,
            extra_patterns=['permission denied', 'not supported', 'unknown userland error', 'illegal option', 'invalid option'] + failure_keywords,
        )
        if command_error:
            return self.fail(
                '점검 명령 실행 실패',
                message=f'Solaris 메모리 사용률 점검에 실패했습니다. 현재 상태: vmstat 출력에서 실행 오류가 확인되었습니다: {command_error}',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        text = (out or '').strip()
        stderr_text = (err or '').strip()
        combined_text = '\n'.join(part for part in (text, stderr_text) if part)
        matched_failure_keywords = [keyword for keyword in failure_keywords if keyword.lower() in combined_text.lower()]
        if matched_failure_keywords:
            return self.fail(
                '메모리 사용률 실패 키워드 감지',
                message=f'Solaris 메모리 사용률 점검에 실패했습니다. 현재 상태: 출력에서 실패 키워드 {matched_failure_keywords}가 확인되었습니다.',
                stdout=text,
                stderr=stderr_text,
            )
        if stderr_text:
            return self.fail(
                '점검 명령 실행 실패',
                message=f'Solaris 메모리 사용률 점검에 실패했습니다. 현재 상태: stderr 출력이 확인되었습니다: {stderr_text}',
                stdout=text,
                stderr=stderr_text,
            )

        row = self._parse_vmstat_row(text)
        if not row:
            return self.fail(
                '메모리 사용률 파싱 실패',
                message='Solaris 메모리 사용률 점검에 실패했습니다. 현재 상태: vmstat 출력에서 헤더와 데이터 행을 정상적으로 해석하지 못했습니다.',
                stdout=text,
                stderr=stderr_text,
            )

        swap_kb = self._to_int(row.get('swap'))
        free_kb = self._to_int(row.get('free'))
        page_in_count = self._to_int(row.get('pi'))
        page_out_count = self._to_int(row.get('po'))
        user_percent = self._to_float(row.get('us'))
        system_percent = self._to_float(row.get('system_percent'))
        idle_percent = self._to_float(row.get('id'))
        run_queue = self._to_int(row.get('r'))
        blocked_queue = self._to_int(row.get('b'))

        if None in (swap_kb, free_kb, page_in_count, page_out_count, user_percent, system_percent, idle_percent):
            return self.fail(
                '메모리 사용률 파싱 실패',
                message='Solaris 메모리 사용률 점검에 실패했습니다. 현재 상태: vmstat 주요 지표(swap, free, pi, po, us, sy, id)를 숫자로 변환하지 못했습니다.',
                stdout=text,
                stderr=stderr_text,
            )

        cpu_busy_percent = round(user_percent + system_percent, 2)
        metrics = {
            'swap_kb': swap_kb,
            'free_kb': free_kb,
            'page_in_count': page_in_count,
            'page_out_count': page_out_count,
            'user_percent': user_percent,
            'system_percent': system_percent,
            'cpu_busy_percent': cpu_busy_percent,
            'idle_percent': idle_percent,
            'run_queue_count': run_queue,
            'blocked_queue_count': blocked_queue,
            'matched_failure_keywords': matched_failure_keywords,
        }

        if free_kb < min_free_kb:
            return self.fail(
                '가용 메모리 부족',
                message=(
                    'Solaris 메모리 사용률이 기준치를 초과했습니다. '
                    f'현재 상태: free {free_kb}KB (기준 {min_free_kb}KB 이상), '
                    f'swap {swap_kb}KB, pi {page_in_count}, po {page_out_count}, '
                    f'run queue {run_queue if run_queue is not None else "N/A"}, '
                    f'blocked {blocked_queue if blocked_queue is not None else "N/A"}, '
                    f'User {user_percent:.2f}%, System {system_percent:.2f}%, '
                    f'User+System {cpu_busy_percent:.2f}%, Idle {idle_percent:.2f}%.'
                ),
                metrics=metrics,
                thresholds={
                    'min_free_kb': min_free_kb,
                    'max_page_in_count': max_page_in_count,
                    'max_page_out_count': max_page_out_count,
                    'failure_keywords': failure_keywords,
                },
                stdout=text,
                stderr=stderr_text,
            )
        if page_in_count > max_page_in_count or page_out_count > max_page_out_count:
            return self.fail(
                '메모리 페이지 입출력 이상',
                message=(
                    'Solaris 메모리 사용률이 기준치를 초과했습니다. '
                    f'현재 상태: pi {page_in_count}회 (기준 {max_page_in_count}회 이하), '
                    f'po {page_out_count}회 (기준 {max_page_out_count}회 이하), '
                    f'free {free_kb}KB, swap {swap_kb}KB, '
                    f'run queue {run_queue if run_queue is not None else "N/A"}, '
                    f'blocked {blocked_queue if blocked_queue is not None else "N/A"}, '
                    f'User {user_percent:.2f}%, System {system_percent:.2f}%, '
                    f'User+System {cpu_busy_percent:.2f}%, Idle {idle_percent:.2f}%.'
                ),
                metrics=metrics,
                thresholds={
                    'min_free_kb': min_free_kb,
                    'max_page_in_count': max_page_in_count,
                    'max_page_out_count': max_page_out_count,
                    'failure_keywords': failure_keywords,
                },
                stdout=text,
                stderr=stderr_text,
            )

        return self.ok(
            metrics=metrics,
            thresholds={
                'min_free_kb': min_free_kb,
                'max_page_in_count': max_page_in_count,
                'max_page_out_count': max_page_out_count,
                'failure_keywords': failure_keywords,
            },
            reasons=(
                f'가용 메모리 {free_kb}KB가 기준 이상이고 '
                f'page in/out 수치도 기준 이내이며 CPU/메모리 병목 징후가 크지 않습니다.'
            ),
            message=(
                'Solaris 메모리 사용률이 정상입니다. '
                f'현재 상태: free {free_kb}KB (기준 {min_free_kb}KB 이상), '
                f'swap {swap_kb}KB, pi {page_in_count}회 (기준 {max_page_in_count}회 이하), '
                f'po {page_out_count}회 (기준 {max_page_out_count}회 이하), '
                f'run queue {run_queue if run_queue is not None else "N/A"}, '
                f'blocked {blocked_queue if blocked_queue is not None else "N/A"}, '
                f'User {user_percent:.2f}%, System {system_percent:.2f}%, '
                f'User+System {cpu_busy_percent:.2f}%, Idle {idle_percent:.2f}%.'
            ),
        )


CHECK_CLASS = Check
