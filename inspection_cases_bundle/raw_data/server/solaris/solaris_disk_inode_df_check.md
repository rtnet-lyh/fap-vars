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

SVR-3-6

# is_required

권고

# inspection_name

I-Node 사용률

# inspection_content

Solaris 서버의 파일시스템별 inode 사용률, 잔여 inode 비율, mount point 영향을 점검합니다.

# inspection_command

```bash
df -o i
```

# inspection_output

```text
Filesystem          iused  ifree %iused Mounted on
/dev/dsk/c0t0d0s0   10234  89765   10%  /
/dev/dsk/c0t0d0s1    5678  12345   30%  /var
```

# description

- `%iused`가 80%를 초과하면 파일시스템 확장 검토.
  - `ifree`가 전체의 20% 미만이면 파일 정리 또는 확장 필요.

# thresholds

[
    {id: null, key: "max_inode_used_percent", value: "80", sortOrder: 0}
,
{id: null, key: "min_inode_free_percent", value: "20", sortOrder: 1}
,
{id: null, key: "failure_keywords", value: "장치를 찾을 수 없습니다,not found,cannot,command not found,module missing", sortOrder: 2}
]

# inspection_script

# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


DF_INODE_COMMAND = 'df -o i'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def _parse_rows(self, text):
        lines = [line.rstrip() for line in (text or '').splitlines() if line.strip()]
        header_found = False
        rows = []

        for index, line in enumerate(lines):
            parts = re.split(r'\s+', line.strip())
            lowered = [part.lower() for part in parts]
            if 'filesystem' in lowered and 'iused' in lowered and 'ifree' in lowered and '%iused' in lowered:
                header_found = True
                continue

            if len(parts) < 5:
                continue
            try:
                inode_used = int(parts[1])
                inode_free = int(parts[2])
                inode_used_percent = float(parts[3].rstrip('%'))
            except ValueError:
                continue
            total_inodes = inode_used + inode_free
            inode_free_percent = round((inode_free / total_inodes) * 100, 2) if total_inodes else 0.0
            rows.append({
                'line_number': index + 1,
                'filesystem': parts[0],
                'inode_used': inode_used,
                'inode_free': inode_free,
                'inode_total': total_inodes,
                'inode_used_percent': inode_used_percent,
                'inode_free_percent': inode_free_percent,
                'mount_point': ' '.join(parts[4:]),
            })
        return {
            'header_found': header_found,
            'rows': rows,
        }

    def _build_mount_summary(self, rows, limit=3):
        if not rows:
            return 'mount 요약 없음'

        summaries = []
        for row in rows[:limit]:
            summaries.append(
                f"{row['mount_point']} inode {row['inode_used_percent']:.2f}% used, free {row['inode_free_percent']:.2f}%"
            )
        if len(rows) > limit:
            summaries.append(f"외 {len(rows) - limit}개")
        return ', '.join(summaries)

    def run(self):
        max_inode_used_percent = self.get_threshold_var('max_inode_used_percent', default=80, value_type='float')
        min_inode_free_percent = self.get_threshold_var('min_inode_free_percent', default=20, value_type='float')
        failure_keywords_raw = self.get_threshold_var('failure_keywords', default='', value_type='str')

        rc, out, err = self._ssh(DF_INODE_COMMAND)
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
                    'Solaris I-Node 사용률 점검에 실패했습니다. '
                    '현재 상태: df -o i 명령을 정상적으로 실행하지 못했습니다.'
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
                    'Solaris I-Node 사용률 점검에 실패했습니다. '
                    f'현재 상태: df -o i 출력에서 실행 오류가 확인되었습니다: {command_error}'
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
                'I-Node 실패 키워드 감지',
                message=(
                    'Solaris I-Node 사용률 점검에 실패했습니다. '
                    f'현재 상태: 출력에서 실패 키워드 {matched_failure_keywords}가 확인되었습니다.'
                ),
                stdout=text,
                stderr=(err or '').strip(),
            )

        parsed = self._parse_rows(text)
        if not parsed['header_found']:
            return self.fail(
                'I-Node 파싱 실패',
                message=(
                    'Solaris I-Node 사용률 점검에 실패했습니다. '
                    '현재 상태: df -o i 출력에서 Filesystem/iused/ifree/%iused 헤더를 찾지 못했습니다.'
                ),
                stdout=text,
                stderr=(err or '').strip(),
            )

        rows = parsed['rows']
        if not rows:
            return self.fail(
                'I-Node 파싱 실패',
                message=(
                    'Solaris I-Node 사용률 점검에 실패했습니다. '
                    '현재 상태: df -o i 출력에서 inode 정보를 해석하지 못했습니다.'
                ),
                stdout=text,
                stderr=(err or '').strip(),
            )

        invalid_rows = [
            row for row in rows
            if row['inode_used'] < 0 or row['inode_free'] < 0 or row['inode_total'] <= 0
        ]
        if invalid_rows:
            invalid_summary = ', '.join(
                f"{row['mount_point']} iused {row['inode_used']} ifree {row['inode_free']}"
                for row in invalid_rows[:3]
            )
            return self.fail(
                'I-Node 데이터 불일치',
                message=(
                    'Solaris I-Node 사용률 점검에 실패했습니다. '
                    f'현재 상태: inode 수치가 비정상입니다: {invalid_summary}.'
                ),
                stdout=text,
                stderr=(err or '').strip(),
            )

        bad_rows = [
            row for row in rows
            if row['inode_used_percent'] > max_inode_used_percent or row['inode_free_percent'] < min_inode_free_percent
        ]
        bad_rows.sort(key=lambda row: (row['inode_used_percent'], -row['inode_free_percent']), reverse=True)
        mount_summary = self._build_mount_summary(bad_rows or sorted(rows, key=lambda row: row['inode_used_percent'], reverse=True))
        if bad_rows:
            top = bad_rows[0]
            return self.fail(
                'I-Node 사용률 임계치 초과',
                message=(
                    'Solaris I-Node 사용률 점검에 실패했습니다. '
                    f'현재 상태: {top["mount_point"]} inode 사용률 {top["inode_used_percent"]:.2f}% '
                    f'(기준 {max_inode_used_percent:.2f}% 이하), 잔여 {top["inode_free_percent"]:.2f}% '
                    f'(기준 {min_inode_free_percent:.2f}% 이상), iused {top["inode_used"]}, '
                    f'ifree {top["inode_free"]}, 영향 mount 요약: {mount_summary}.'
                ),
                stdout=text,
                stderr=(err or '').strip(),
            )

        max_row = max(rows, key=lambda item: item['inode_used_percent'])
        min_free_row = min(rows, key=lambda item: item['inode_free_percent'])
        return self.ok(
            metrics={
                'filesystem_count': len(rows),
                'max_inode_used_mount_point': max_row['mount_point'],
                'max_inode_used_percent': max_row['inode_used_percent'],
                'min_inode_free_mount_point': min_free_row['mount_point'],
                'min_inode_free_percent': min_free_row['inode_free_percent'],
                'rows': rows,
                'matched_failure_keywords': matched_failure_keywords,
            },
            thresholds={
                'max_inode_used_percent': max_inode_used_percent,
                'min_inode_free_percent': min_inode_free_percent,
                'failure_keywords': failure_keywords,
            },
            reasons=(
                f'모든 파일시스템의 inode 사용률과 잔여 inode 비율이 기준 이내입니다. '
                f'최대 사용률은 {max_row["mount_point"]} {max_row["inode_used_percent"]:.2f}%입니다.'
            ),
            message=(
                'Solaris I-Node 사용률이 정상입니다. '
                f'현재 상태: 파일시스템 {len(rows)}개, 최대 inode 사용률 {max_row["mount_point"]} {max_row["inode_used_percent"]:.2f}% '
                f'(기준 {max_inode_used_percent:.2f}% 이하), 최소 잔여율 {min_free_row["mount_point"]} {min_free_row["inode_free_percent"]:.2f}% '
                f'(기준 {min_inode_free_percent:.2f}% 이상), 영향 mount 요약: {mount_summary}.'
            ),
        )


CHECK_CLASS = Check
