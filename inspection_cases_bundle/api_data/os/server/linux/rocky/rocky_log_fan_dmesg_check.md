# type_name

일상점검

# area_name

server

# category_name

상태점검

# application_type

linux

# application

rocky

# inspection_code

U-REPLAY-DMESG-FAN-01

# is_required

필수

# inspection_name

FAN 로그

# inspection_content

FAN 작동 이상 유무 점검(FAN Fail)

# inspection_command

```bash
dmesg | grep -Ei 'fan|fan fail'
```

# inspection_output

```text
[   10.234567] ipmi_si dmi-ipmi-si.0: Fan1 RPM lower critical - going low
[   10.235104] ipmi_si dmi-ipmi-si.0: Fan2 RPM lower non-recoverable - fan fail
[   10.235882] hwmon hwmon2: fan1 input not responding
[   10.236451] platform sensor_fan: cooling fan failure detected
[   10.237018] systemd[1]: Warning: chassis fan status is critical
```

# description

- (팬 오류 메시지) fan 또는 fan fail 메시지가 발견되면, 냉각 장치 이상 또는 회전수 저하가 발생했을 가능성이 있으므로 하드웨어 점검이 필요
- (회전수 임계치 메시지) RPM lower critical, non-recoverable 메시지가 확인되면 팬 속도가 임계치 이하로 떨어진 상태이므로 즉시 점검 권고
- (팬 응답 이상) fan input not responding 메시지가 발견되면 팬 센서 또는 팬 장치 이상 여부를 확인해야 함
- (냉각 장애) cooling fan failure detected 메시지가 발견되면 시스템 과열 위험이 있으므로 장비 상태 점검 및 팬 교체 검토 필요

- **양호**: `dmesg | grep -Ei 'fan|fan fail'` 결과에 관련 로그가 출력되지 않는 상태
- **경고**: `dmesg | grep -Ei 'fan|fan fail'` 결과에 팬 오류, 팬 속도 저하, 팬 장애 관련 로그가 하나 이상 출력되는 상태
- **참고**: 본 항목은 관련 로그 출력 여부를 기준으로 판단하며, 출력 결과가 존재하면 팬 장애 또는 냉각 이상 징후로 간주함

# thresholds

[
    {id: null, key: "fan_error_keywords", value: "fan fail|rpm lower critical|non-recoverable|fan input not responding|cooling fan failure|fan status is critical", sortOrder: 0}
]

# inspection_script

# -*- coding: utf-8 -*-

from .common._base import BaseCheck


DMESG_FAN_COMMAND = "dmesg | grep -Ei 'fan|fan fail'"


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def _split_keywords(self, raw_value):
        return [
            token.strip()
            for token in str(raw_value or '').split('|')
            if token.strip()
        ]

    def _find_matches(self, lines, keywords):
        matches = []

        for line in lines:
            lowered = line.lower()
            matched_keywords = [
                keyword
                for keyword in keywords
                if keyword.lower() in lowered
            ]
            if not matched_keywords:
                continue
            matches.append({
                'line': line,
                'matched_keywords': matched_keywords,
            })

        return matches

    def _count_keywords(self, matches, keywords):
        counts = {keyword: 0 for keyword in keywords}

        for match in matches:
            for keyword in match.get('matched_keywords', []):
                if keyword in counts:
                    counts[keyword] += 1

        return counts

    def _format_keyword_counts(self, counts):
        return ', '.join(
            f'{keyword}={count}건'
            for keyword, count in counts.items()
        )

    def run(self):
        fan_error_keywords = self._split_keywords(
            self.get_threshold_var(
                'fan_error_keywords',
                default='fan fail|rpm lower critical|non-recoverable|fan input not responding|cooling fan failure|fan status is critical',
                value_type='str',
            )
        )
        if not fan_error_keywords:
            return self.fail(
                '임계치 미정의',
                message='fan_error_keywords 가 정의되어 있지 않습니다.',
            )

        rc, out, err = self._ssh(DMESG_FAN_COMMAND)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'SSH 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if rc not in (0, 1):
            return self.fail(
                '점검 명령 실행 실패',
                message='dmesg FAN 로그 점검 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        lines = [line.strip() for line in (out or '').splitlines() if line.strip()]
        matches = self._find_matches(lines, fan_error_keywords)
        keyword_counts = self._count_keywords(matches, fan_error_keywords)
        threshold_summary = 'fan_error_keywords=' + '|'.join(fan_error_keywords)

        metrics = {
            'grep_line_count': len(lines),
            'fan_error_match_count': len(matches),
            'fan_error_keyword_counts': keyword_counts,
            'fan_error_matches': matches,
            'grep_lines': lines,
        }
        thresholds = {
            'fan_error_keywords': '|'.join(fan_error_keywords),
        }

        if matches:
            return self.warn(
                metrics=metrics,
                thresholds=thresholds,
                reasons='팬 장애 관련 키워드가 확인되었습니다. 키워드별 검출 건수: ' + self._format_keyword_counts(keyword_counts),
                message=(
                    '팬 장애 관련 dmesg 로그가 확인되었습니다. '
                    '키워드별 검출 건수: ' + self._format_keyword_counts(keyword_counts) +
                    '. 임계치: ' + threshold_summary
                ),
            )

        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='팬 장애 관련 키워드가 검출되지 않았습니다. 키워드별 검출 건수: ' + self._format_keyword_counts(keyword_counts),
            message=(
                'FAN 로그 점검이 정상 수행되었습니다. '
                '미검출 키워드 현황: ' + self._format_keyword_counts(keyword_counts) +
                '. 임계치: ' + threshold_summary
            ),
        )


CHECK_CLASS = Check
