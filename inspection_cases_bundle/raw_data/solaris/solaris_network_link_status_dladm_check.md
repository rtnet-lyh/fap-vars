# type_name

일상점검(상태점검)

# area_name

서버

# category_name

NETWORK

# application_type

UNIX

# application

solaris

# inspection_code

SVR-7-1

# is_required

필수

# inspection_name

NW 링크 상태 연결속도 설정

# inspection_content

`dladm show-phys` 출력으로 물리 네트워크 링크의 연결 상태, 속도, duplex 설정이 운영 기준과 일치하는지 점검합니다.

# inspection_command

```bash
dladm show-phys
```

# inspection_output

```text
LINK     MEDIA      STATE    SPEED   DUPLEX
e1000g0  1000baseT  up       1000    full
e1000g1  1000baseT  down     1000    full
e1000g2  1000baseT  unknown  1000    full
```

# description

- `STATE`는 `up`이어야 정상.
  - `down` 또는 `unknown`이면 인터페이스, 케이블, 설정 점검 필요.
  - `SPEED`, `DUPLEX`가 설정값과 일치하는지 확인.

# thresholds

[
    {id: null, key: "required_state", value: "up", sortOrder: 0}
,
{id: null, key: "expected_speed_map", value: "e1000g0:1000,e1000g1:1000,e1000g2:1000", sortOrder: 1}
,
{id: null, key: "expected_duplex_map", value: "e1000g0:full,e1000g1:full,e1000g2:full", sortOrder: 2}
,
{id: null, key: "failure_keywords", value: "장치를 찾을 수 없습니다,not found,module,cannot,command not found,no such file", sortOrder: 3}
]

# inspection_script

# -*- coding: utf-8 -*-

import re

from .common._base import BaseCheck


DLADM_SHOW_PHYS_COMMAND = 'dladm show-phys'


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def _split_keywords(self, raw_value):
        return [token.strip() for token in str(raw_value or '').split(',') if token.strip()]

    def _split_csv_map(self, raw_value):
        mapping = {}
        for token in self._split_keywords(raw_value):
            if ':' not in token:
                continue
            key, value = token.split(':', 1)
            key = key.strip()
            value = value.strip()
            if key and value:
                mapping[key] = value
        return mapping

    def _parse_int(self, value):
        try:
            return int(str(value).strip())
        except (TypeError, ValueError):
            return None

    def _parse_show_phys_rows(self, text):
        lines = [line.rstrip() for line in (text or '').splitlines() if line.strip()]
        if not lines:
            return {
                'header_found': False,
                'rows': [],
            }

        header_found = False
        rows = []
        for index, line in enumerate(lines):
            parts = re.split(r'\s+', line.strip())
            lowered = [part.lower() for part in parts]

            if not header_found:
                if {'link', 'media', 'state', 'speed', 'duplex'}.issubset(set(lowered)):
                    header_found = True
                continue

            if len(parts) < 5:
                continue

            link_name = parts[0]
            media = parts[1]
            state = parts[2].lower()
            speed = self._parse_int(parts[3])
            duplex = parts[4].lower()

            rows.append({
                'line_number': index + 1,
                'raw_line': line.strip(),
                'link_name': link_name,
                'media': media,
                'state': state,
                'speed_mbps': speed,
                'duplex': duplex,
            })

        return {
            'header_found': header_found,
            'rows': rows,
        }

    def _build_link_summary(self, rows, limit=3):
        if not rows:
            return '링크 요약 없음'

        parts = []
        for row in rows[:limit]:
            speed_value = row['speed_mbps'] if row['speed_mbps'] is not None else 'N/A'
            parts.append(
                f"{row['link_name']} state={row['state']}, speed={speed_value}, duplex={row['duplex']}"
            )
        if len(rows) > limit:
            parts.append(f'외 {len(rows) - limit}건')
        return ', '.join(parts)

    def run(self):
        required_state = self.get_threshold_var('required_state', default='up', value_type='str').strip().lower()
        expected_speeds = self._split_csv_map(
            self.get_threshold_var('expected_speed_map', default='', value_type='str')
        )
        expected_duplexes = {
            key: value.lower()
            for key, value in self._split_csv_map(
                self.get_threshold_var('expected_duplex_map', default='', value_type='str')
            ).items()
        }
        failure_keywords = self._split_keywords(
            self.get_threshold_var(
                'failure_keywords',
                default='장치를 찾을 수 없습니다,not found,module,cannot,command not found,no such file',
                value_type='str',
            )
        )

        rc, out, err = self._ssh(DLADM_SHOW_PHYS_COMMAND)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'SSH 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        text = (out or '').strip()
        stderr_text = (err or '').strip()
        combined_text = '\n'.join(part for part in (text, stderr_text) if part)

        command_error = self._detect_command_error(
            text,
            stderr_text,
            extra_patterns=failure_keywords + [
                'permission denied',
                'illegal option',
                'invalid option',
                'usage:',
                'not supported',
                'unknown userland error',
            ],
        )
        if command_error:
            return self.fail(
                '점검 명령 실행 실패',
                message=(
                    'Solaris Network 연결상태 정상 유무 점검에 실패했습니다. '
                    f'현재 상태: dladm show-phys 출력에서 실행 오류가 확인되었습니다: {command_error}'
                ),
                stdout=text,
                stderr=stderr_text,
            )

        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message=(
                    'Solaris Network 연결상태 정상 유무 점검에 실패했습니다. '
                    f'현재 상태: dladm show-phys 명령 종료코드가 rc={rc}로 반환되었습니다.'
                ),
                stdout=text,
                stderr=stderr_text,
            )

        matched_failure_keywords = [
            keyword for keyword in failure_keywords
            if keyword.lower() in combined_text.lower()
        ]
        if matched_failure_keywords:
            return self.fail(
                '네트워크 링크 실패 키워드 감지',
                message=(
                    'Solaris Network 연결상태 정상 유무 점검에 실패했습니다. '
                    f'현재 상태: 출력에서 실패 키워드 {matched_failure_keywords}가 확인되었습니다.'
                ),
                stdout=text,
                stderr=stderr_text,
            )

        if stderr_text:
            return self.fail(
                '점검 명령 실행 실패',
                message=(
                    'Solaris Network 연결상태 정상 유무 점검에 실패했습니다. '
                    f'현재 상태: stderr 출력이 확인되었습니다: {stderr_text}'
                ),
                stdout=text,
                stderr=stderr_text,
            )

        if not text:
            return self.fail(
                '네트워크 링크 파싱 실패',
                message='Solaris Network 연결상태 정상 유무 점검에 실패했습니다. 현재 상태: dladm show-phys 출력이 비어 있어 링크 상태를 해석하지 못했습니다.',
                stdout=text,
                stderr=stderr_text,
            )

        parsed = self._parse_show_phys_rows(text)
        if not parsed['header_found']:
            return self.fail(
                '네트워크 링크 파싱 실패',
                message=(
                    'Solaris Network 연결상태 정상 유무 점검에 실패했습니다. '
                    '현재 상태: dladm show-phys 출력에서 LINK/MEDIA/STATE/SPEED/DUPLEX 헤더를 찾지 못했습니다.'
                ),
                stdout=text,
                stderr=stderr_text,
            )

        rows = parsed['rows']
        if not rows:
            return self.fail(
                '네트워크 링크 파싱 실패',
                message=(
                    'Solaris Network 연결상태 정상 유무 점검에 실패했습니다. '
                    '현재 상태: dladm show-phys 출력에서 링크 정보를 해석하지 못했습니다.'
                ),
                stdout=text,
                stderr=stderr_text,
            )

        invalid_rows = [row for row in rows if row['speed_mbps'] is None]
        if invalid_rows:
            return self.fail(
                '네트워크 링크 파싱 실패',
                message=(
                    'Solaris Network 연결상태 정상 유무 점검에 실패했습니다. '
                    f'현재 상태: 링크 속도를 숫자로 해석하지 못한 항목이 있습니다. 첫 항목: {invalid_rows[0]["raw_line"]}.'
                ),
                stdout=text,
                stderr=stderr_text,
            )

        abnormal_state_rows = [row for row in rows if required_state and row['state'] != required_state]
        speed_mismatch_rows = []
        for row in rows:
            expected_speed = expected_speeds.get(row['link_name'])
            if expected_speed is None:
                continue
            expected_speed_value = self._parse_int(expected_speed)
            if expected_speed_value is None or row['speed_mbps'] != expected_speed_value:
                speed_mismatch_rows.append({
                    'link_name': row['link_name'],
                    'expected_speed_mbps': expected_speed,
                    'actual_speed_mbps': row['speed_mbps'],
                    'raw_line': row['raw_line'],
                })

        duplex_mismatch_rows = []
        for row in rows:
            expected_duplex = expected_duplexes.get(row['link_name'])
            if expected_duplex is None:
                continue
            if row['duplex'] != expected_duplex:
                duplex_mismatch_rows.append({
                    'link_name': row['link_name'],
                    'expected_duplex': expected_duplex,
                    'actual_duplex': row['duplex'],
                    'raw_line': row['raw_line'],
                })

        metrics = {
            'command_rc': rc,
            'link_count': len(rows),
            'up_count': sum(1 for row in rows if row['state'] == 'up'),
            'down_count': sum(1 for row in rows if row['state'] == 'down'),
            'unknown_count': sum(1 for row in rows if row['state'] == 'unknown'),
            'abnormal_state_count': len(abnormal_state_rows),
            'speed_mismatch_count': len(speed_mismatch_rows),
            'duplex_mismatch_count': len(duplex_mismatch_rows),
            'matched_failure_keywords': matched_failure_keywords,
            'links': rows,
        }
        thresholds = {
            'required_state': required_state,
            'expected_speed_map': expected_speeds,
            'expected_duplex_map': expected_duplexes,
            'failure_keywords': failure_keywords,
        }

        if abnormal_state_rows:
            first_row = abnormal_state_rows[0]
            return self.fail(
                '네트워크 링크 상태 이상',
                message=(
                    'Solaris Network 연결상태 정상 유무 점검에 실패했습니다. '
                    f'현재 상태: 링크 {first_row["link_name"]}가 {first_row["state"]} 상태이며 기준은 {required_state}입니다. '
                    f'speed {first_row["speed_mbps"]}Mbps, duplex {first_row["duplex"]}. '
                    f'링크 요약: {self._build_link_summary(rows)}.'
                ),
                metrics=metrics,
                thresholds=thresholds,
                stdout=text,
                stderr=stderr_text,
            )

        if speed_mismatch_rows:
            first_mismatch = speed_mismatch_rows[0]
            return self.fail(
                '네트워크 링크 속도 설정 이상',
                message=(
                    'Solaris Network 연결상태 정상 유무 점검에 실패했습니다. '
                    f'현재 상태: 링크 {first_mismatch["link_name"]} 속도가 {first_mismatch["actual_speed_mbps"]}Mbps이며 '
                    f'기준은 {first_mismatch["expected_speed_mbps"]}Mbps입니다. '
                    f'링크 요약: {self._build_link_summary(rows)}.'
                ),
                metrics=metrics,
                thresholds=thresholds,
                stdout=text,
                stderr=stderr_text,
            )

        if duplex_mismatch_rows:
            first_mismatch = duplex_mismatch_rows[0]
            return self.fail(
                '네트워크 링크 Duplex 설정 이상',
                message=(
                    'Solaris Network 연결상태 정상 유무 점검에 실패했습니다. '
                    f'현재 상태: 링크 {first_mismatch["link_name"]} duplex가 {first_mismatch["actual_duplex"]}이며 '
                    f'기준은 {first_mismatch["expected_duplex"]}입니다. '
                    f'링크 요약: {self._build_link_summary(rows)}.'
                ),
                metrics=metrics,
                thresholds=thresholds,
                stdout=text,
                stderr=stderr_text,
            )

        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons=(
                f'링크 {len(rows)}개가 모두 {required_state} 상태로 확인되었고 '
                '속도와 duplex 설정도 지정한 기준과 일치합니다.'
            ),
            message=(
                'Solaris Network 연결상태가 정상입니다. '
                f'현재 상태: 링크 {len(rows)}개, up {metrics["up_count"]}개, down {metrics["down_count"]}개, '
                f'unknown {metrics["unknown_count"]}개, 속도 불일치 {metrics["speed_mismatch_count"]}개, '
                f'duplex 불일치 {metrics["duplex_mismatch_count"]}개입니다. '
                f'링크 요약: {self._build_link_summary(rows)}.'
            ),
        )


CHECK_CLASS = Check
