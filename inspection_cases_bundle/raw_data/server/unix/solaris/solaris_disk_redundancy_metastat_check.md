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

SVR-3-3

# is_required

권고

# inspection_name

Disk 이중화 정상 여부

# inspection_content

Solaris Volume Manager mirror 상태, submirror 상태, 정상 status 문구를 기준으로 디스크 이중화 정상 여부를 점검합니다.

# inspection_command

```bash
metastat
```

# inspection_output

```text
d0: Mirror
    Submirror 0: d10
      State: Okay
    Submirror 1: d11
      State: Okay
    State: Okay
    Status: The volume is functioning properly.

d10: Submirror of d0
    State: Okay

d11: Submirror of d0
    State: Okay
```

# description

- RAID 미러 볼륨 `d0`의 상태는 `Okay`여야 함.
  - `Maintenance` 상태면 디스크 이상 가능성이 있으므로 점검 필요.
  - `Status`는 `The volume is functioning properly.`가 정상.

# thresholds

[
    {id: null, key: "required_state", value: "Okay", sortOrder: 0}
,
{id: null, key: "min_submirror_count", value: "2", sortOrder: 1}
,
{id: null, key: "failure_keywords", value: "장치를 찾을 수 없습니다,not found,cannot,command not found,module missing", sortOrder: 2}
]

# inspection_script

# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


METASTAT_COMMAND = 'metastat'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def _split_blocks(self, text):
        sections = [section.strip() for section in re.split(r'\n\s*\n', (text or '').strip()) if section.strip()]
        return sections

    def _parse_mirror_blocks(self, text):
        mirror_entries = []
        submirror_state_map = {}
        sections = self._split_blocks(text)

        for section in sections:
            lines = [line.rstrip() for line in section.splitlines() if line.strip()]
            if not lines:
                continue

            first_line = lines[0].strip()
            submirror_match = re.match(r'^(d\d+):\s+Submirror of\s+(d\d+)$', first_line)
            if submirror_match:
                submirror_name = submirror_match.group(1)
                parent_mirror = submirror_match.group(2)
                submirror_state_match = re.search(r'^\s*State:\s*(.+)$', section, re.MULTILINE)
                submirror_state_map[submirror_name] = {
                    'parent_mirror': parent_mirror,
                    'state': submirror_state_match.group(1).strip() if submirror_state_match else '',
                }
                continue

            mirror_match = re.match(r'^(d\d+):\s+Mirror$', first_line)
            if not mirror_match:
                continue

            mirror_name = mirror_match.group(1)
            submirrors = re.findall(r'^\s*Submirror\s+\d+:\s+(\S+)$', section, re.MULTILINE)
            state_matches = re.findall(r'^\s*State:\s*(.+)$', section, re.MULTILINE)
            overall_state = state_matches[-1].strip() if state_matches else ''
            status_match = re.search(r'^\s*Status:\s*(.+)$', section, re.MULTILINE)
            status_text = status_match.group(1).strip() if status_match else ''

            mirror_entries.append({
                'mirror_name': mirror_name,
                'submirrors': submirrors,
                'mirror_state': overall_state,
                'mirror_status': status_text,
                'section': section,
            })

        return {
            'mirrors': mirror_entries,
            'submirror_state_map': submirror_state_map,
        }

    def _build_mirror_summary(self, mirrors, limit=3):
        if not mirrors:
            return 'mirror 요약 없음'

        summaries = []
        for mirror in mirrors[:limit]:
            summaries.append(
                f"{mirror['mirror_name']} state={mirror['mirror_state'] or 'unknown'}, submirror {len(mirror['submirrors'])}개"
            )
        if len(mirrors) > limit:
            summaries.append(f"외 {len(mirrors) - limit}개")
        return ', '.join(summaries)

    def run(self):
        required_state = self.get_threshold_var('required_state', default='Okay', value_type='str')
        min_submirror_count = self.get_threshold_var('min_submirror_count', default=2, value_type='int')
        failure_keywords_raw = self.get_threshold_var('failure_keywords', default='', value_type='str')

        rc, out, err = self._ssh(METASTAT_COMMAND)

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
                    'Solaris Disk 이중화 점검에 실패했습니다. '
                    '현재 상태: metastat 명령을 정상적으로 실행하지 못했습니다.'
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
                    'Solaris Disk 이중화 점검에 실패했습니다. '
                    f'현재 상태: metastat 출력에서 실행 오류가 확인되었습니다: {command_error}'
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
                'Disk 이중화 실패 키워드 감지',
                message=(
                    'Solaris Disk 이중화 점검에 실패했습니다. '
                    f'현재 상태: 출력에서 실패 키워드 {matched_failure_keywords}가 확인되었습니다.'
                ),
                stdout=text,
                stderr=(err or '').strip(),
            )

        parsed = self._parse_mirror_blocks(text)
        mirrors = parsed['mirrors']
        submirror_state_map = parsed['submirror_state_map']
        if not mirrors:
            return self.fail(
                'Mirror 정보 없음',
                message=(
                    'Solaris Disk 이중화 점검에 실패했습니다. '
                    '현재 상태: metastat 출력에서 Mirror 볼륨 정보를 찾지 못했습니다.'
                ),
                stdout=text,
                stderr=(err or '').strip(),
            )

        mirror_summary = self._build_mirror_summary(mirrors)
        abnormal_mirrors = []
        abnormal_submirrors = []
        missing_status_mirrors = []
        insufficient_submirrors = []

        for mirror in mirrors:
            mirror_name = mirror['mirror_name']
            submirrors = mirror['submirrors']
            mirror_state = mirror['mirror_state']
            status_text = mirror['mirror_status']

            if len(submirrors) < min_submirror_count:
                insufficient_submirrors.append(f'{mirror_name}={len(submirrors)}')

            if mirror_state.lower() != required_state.lower():
                abnormal_mirrors.append(f'{mirror_name}={mirror_state or "unknown"}')

            if 'functioning properly' not in status_text.lower():
                missing_status_mirrors.append(f'{mirror_name}={status_text or "unknown"}')

            for submirror_name in submirrors:
                submirror_info = submirror_state_map.get(submirror_name, {})
                submirror_state = (submirror_info.get('state') or '').strip()
                if submirror_state.lower() != required_state.lower():
                    abnormal_submirrors.append(f'{submirror_name}={submirror_state or "unknown"}')

        if insufficient_submirrors:
            return self.fail(
                'Submirror 수 부족',
                message=(
                    'Solaris Disk 이중화 점검에 실패했습니다. '
                    f'현재 상태: 기준 {min_submirror_count}개 이상을 만족하지 못한 mirror가 있습니다: {insufficient_submirrors}. '
                    f'mirror 요약: {mirror_summary}.'
                ),
                stdout=text,
                stderr=(err or '').strip(),
            )

        if abnormal_mirrors or abnormal_submirrors or missing_status_mirrors:
            return self.fail(
                'Disk 이중화 상태 비정상',
                message=(
                    'Solaris Disk 이중화 점검에 실패했습니다. '
                    f'현재 상태: 비정상 mirror={abnormal_mirrors or ["없음"]}, '
                    f'비정상 submirror={abnormal_submirrors or ["없음"]}, '
                    f'정상 status 미확인 mirror={missing_status_mirrors or ["없음"]}, '
                    f'mirror 요약: {mirror_summary}.'
                ),
                stdout=text,
                stderr=(err or '').strip(),
            )

        primary_mirror = mirrors[0]
        return self.ok(
            metrics={
                'mirror_count': len(mirrors),
                'mirror_name': primary_mirror['mirror_name'],
                'submirror_count': len(primary_mirror['submirrors']),
                'mirror_state': primary_mirror['mirror_state'],
                'mirror_status': primary_mirror['mirror_status'],
                'submirrors': primary_mirror['submirrors'],
                'mirror_rows': mirrors,
                'submirror_state_map': submirror_state_map,
                'matched_failure_keywords': matched_failure_keywords,
            },
            thresholds={
                'required_state': required_state,
                'min_submirror_count': min_submirror_count,
                'failure_keywords': failure_keywords,
            },
            reasons=(
                f'mirror {len(mirrors)}개와 submirror 상태가 모두 {required_state}이며 '
                '정상 status 문구도 확인되었습니다.'
            ),
            message=(
                'Solaris Disk 이중화가 정상입니다. '
                f'현재 상태: mirror {len(mirrors)}개, 대표 mirror {primary_mirror["mirror_name"]} '
                f'state={primary_mirror["mirror_state"]}, status={primary_mirror["mirror_status"]}, '
                f'submirror {len(primary_mirror["submirrors"])}개 (기준 {min_submirror_count}개 이상), '
                f'mirror 요약: {mirror_summary}.'
            ),
        )


CHECK_CLASS = Check
