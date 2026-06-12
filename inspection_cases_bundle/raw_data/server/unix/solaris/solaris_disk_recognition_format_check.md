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

SVR-3-4

# is_required

권고

# inspection_name

Disk 인식 여부 점검

# inspection_content

시스템이 디스크 목록을 정상적으로 표시하는지, 각 디스크가 비정상 문구 없이 인식되는지를 기준으로 디스크 인식 상태를 점검합니다.

# inspection_command

```bash
format
```

# inspection_output

```text
AVAILABLE DISK SELECTIONS:
0. c0t0d0 <ST3200822AS> (16.8GB)
1. c0t1d0 <ST3200822AS> (16.8GB)
2. c0t2d0 <ST3200822AS> (16.8GB)
3. c0t3d0 <ST3200822AS> (16.8GB)
Specify disk (enter its number):
```

# description

- 모든 디스크가 `AVAILABLE DISK SELECTIONS`에 정상 표시되어야 함.
  - `Unknown` 또는 `Drive not available`이면 장치 점검 필요.

# thresholds

[
    {id: null, key: "expected_disk_count", value: "1", sortOrder: 0}
,
{id: null, key: "failure_keywords", value: "Unknown,Drive not available,장치를 찾을 수 없습니다,not found,cannot,command not found,module missing", sortOrder: 1}
]

# inspection_script

# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


FORMAT_COMMAND = "printf '\\n' | format"


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def _parse_disk_entries(self, text):
        lines = [line.rstrip() for line in (text or '').splitlines() if line.strip()]
        header_found = False
        prompt_found = False
        disk_entries = []

        for index, line in enumerate(lines):
            stripped = line.strip()
            lowered = stripped.lower()

            if stripped == 'AVAILABLE DISK SELECTIONS:':
                header_found = True
                continue

            if lowered.startswith('specify disk'):
                prompt_found = True
                continue

            entry_match = re.match(r'^(\d+)\.\s+(\S+)(?:\s+(.+))?$', stripped)
            if not entry_match:
                continue

            selection_index = int(entry_match.group(1))
            device_name = entry_match.group(2)
            detail_text = (entry_match.group(3) or '').strip()
            disk_entries.append({
                'line_number': index + 1,
                'selection_index': selection_index,
                'device_name': device_name,
                'detail_text': detail_text,
                'is_unknown': 'unknown' in detail_text.lower(),
                'is_unavailable': 'drive not available' in detail_text.lower(),
            })

        return {
            'header_found': header_found,
            'prompt_found': prompt_found,
            'disk_entries': disk_entries,
        }

    def _build_disk_summary(self, disk_entries, limit=4):
        if not disk_entries:
            return '디스크 요약 없음'

        summaries = []
        for disk in disk_entries[:limit]:
            detail = f" {disk['detail_text']}" if disk['detail_text'] else ''
            summaries.append(f"{disk['selection_index']}.{disk['device_name']}{detail}".strip())
        if len(disk_entries) > limit:
            summaries.append(f"외 {len(disk_entries) - limit}개")
        return ', '.join(summaries)

    def run(self):
        expected_disk_count = self.get_threshold_var('expected_disk_count', default=1, value_type='int')
        failure_keywords_raw = self.get_threshold_var('failure_keywords', default='Unknown,Drive not available', value_type='str')

        rc, out, err = self._ssh(FORMAT_COMMAND)

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
                    'Solaris Disk 인식 점검에 실패했습니다. '
                    '현재 상태: format 명령을 정상적으로 실행하지 못했습니다.'
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
                    'Solaris Disk 인식 점검에 실패했습니다. '
                    f'현재 상태: format 출력에서 실행 오류가 확인되었습니다: {command_error}'
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
                'Disk 인식 실패 키워드 감지',
                message=(
                    'Solaris Disk 인식 점검에 실패했습니다. '
                    f'현재 상태: 출력에서 실패 키워드 {matched_failure_keywords}가 확인되었습니다.'
                ),
                stdout=text,
                stderr=(err or '').strip(),
            )

        parsed = self._parse_disk_entries(text)
        if not parsed['header_found']:
            return self.fail(
                'Disk 인식 정보 없음',
                message=(
                    'Solaris Disk 인식 점검에 실패했습니다. '
                    '현재 상태: format 출력에서 AVAILABLE DISK SELECTIONS 헤더를 찾지 못했습니다.'
                ),
                stdout=text,
                stderr=(err or '').strip(),
            )

        disk_entries = parsed['disk_entries']
        if not disk_entries:
            return self.fail(
                'Disk 인식 정보 없음',
                message=(
                    'Solaris Disk 인식 점검에 실패했습니다. '
                    '현재 상태: format 출력에서 디스크 선택 목록을 해석하지 못했습니다.'
                ),
                stdout=text,
                stderr=(err or '').strip(),
            )

        if not parsed['prompt_found']:
            return self.fail(
                'Disk 선택 프롬프트 없음',
                message=(
                    'Solaris Disk 인식 점검에 실패했습니다. '
                    '현재 상태: format 출력에서 Specify disk 프롬프트를 찾지 못했습니다.'
                ),
                stdout=text,
                stderr=(err or '').strip(),
            )

        unknown_disks = [disk for disk in disk_entries if disk['is_unknown'] or disk['is_unavailable']]
        if len(disk_entries) < expected_disk_count:
            return self.fail(
                'Disk 수 부족',
                message=(
                    'Solaris Disk 인식 점검에 실패했습니다. '
                    f'현재 상태: 인식 디스크 {len(disk_entries)}개로 집계되어 기준 {expected_disk_count}개 이상을 만족하지 못했습니다. '
                    f'디스크 요약: {self._build_disk_summary(disk_entries)}.'
                ),
                stdout=text,
                stderr=(err or '').strip(),
            )

        if unknown_disks:
            abnormal_summary = ', '.join(
                f"{disk['selection_index']}.{disk['device_name']} {disk['detail_text']}".strip()
                for disk in unknown_disks[:4]
            )
            return self.fail(
                'Disk 인식 상태 비정상',
                message=(
                    'Solaris Disk 인식 점검에 실패했습니다. '
                    f'현재 상태: 비정상 디스크가 확인되었습니다: {abnormal_summary}.'
                ),
                stdout=text,
                stderr=(err or '').strip(),
            )

        disk_names = [disk['device_name'] for disk in disk_entries]
        return self.ok(
            metrics={
                'disk_count': len(disk_entries),
                'disk_names': disk_names,
                'disk_rows': disk_entries,
                'matched_failure_keywords': matched_failure_keywords,
            },
            thresholds={
                'expected_disk_count': expected_disk_count,
                'failure_keywords': failure_keywords,
            },
            reasons=(
                f'디스크 {len(disk_entries)}개가 정상적으로 표시되었고 Unknown 또는 Drive not available 문구가 없습니다.'
            ),
            message=(
                'Solaris Disk 인식이 정상입니다. '
                f'현재 상태: 디스크 {len(disk_entries)}개 (기준 {expected_disk_count}개 이상), '
                f'디스크 요약: {self._build_disk_summary(disk_entries)}.'
            ),
        )


CHECK_CLASS = Check
