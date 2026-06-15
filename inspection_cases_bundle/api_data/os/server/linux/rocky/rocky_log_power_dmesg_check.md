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


SV-LIN-RKY-009

# is_required

필수

# inspection_name

POWER 로그

# inspection_content

전원공급장치 오류 및 이상 유무 점검(PS Failed)

# inspection_command

```bash
dmesg | grep -Ei 'power|psu|PS Failed'
```

# inspection_output

```text
[   18.123456] ipmi_si dmi-ipmi-si.0: Power supply PSU1 failure detected
[   18.124102] ipmi_si dmi-ipmi-si.0: PSU2 status changed: predictive failure
[   18.124889] platform power_mon: PS Failed alarm asserted
[   18.125401] hwmon hwmon3: power unit input lost
[   18.126033] systemd[1]: Warning: redundant power supply degraded
```

# description

- (전원 오류 메시지) power, PSU, PS Failed 관련 메시지가 발견되면 전원 공급 장치 이상 또는 이중화 전원 상태 저하 가능성이 있으므로 하드웨어 점검 필요
- (PSU 장애 메시지) PSU failure detected 또는 predictive failure 메시지가 확인되면 전원 공급 장치 고장 또는 고장 예측 상태를 의미하므로 PSU 상태 점검 및 교체 검토 필요
- (전원 입력 상실) power unit input lost 메시지가 발견되면 전원 입력 문제, 케이블 불량, 전원 모듈 이상 여부를 확인해야 함
- (이중화 전원 저하) redundant power supply degraded 메시지가 확인되면 이중화 전원 구성 중 일부가 비정상 상태일 수 있으므로 즉시 점검 권고

- **양호**: `dmesg | grep -Ei 'power|psu|PS Failed'` 결과에 관련 로그가 출력되지 않는 상태
- **경고**: `dmesg | grep -Ei 'power|psu|PS Failed'` 결과에 전원 공급 장치 오류, PSU 장애, 전원 입력 상실, PS Failed 관련 로그가 하나 이상 출력되는 상태
- **참고**: 본 항목은 관련 로그 출력 여부를 기준으로 판단하며, 출력 결과가 존재하면 전원 장치 또는 전원 이중화 이상 징후로 간주함

# thresholds

[
    {id: null, key: "power_error_keywords", value: "power supply failure detected|predictive failure|ps failed|power unit input lost|redundant power supply degraded", sortOrder: 0}
]

# inspection_script

# -*- coding: utf-8 -*-

from .common._base import BaseCheck


DMESG_POWER_COMMAND = "dmesg | grep -Ei 'power|psu|PS Failed'"


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
        power_error_keywords = self._split_keywords(
            self.get_threshold_var(
                'power_error_keywords',
                default='power supply failure detected|predictive failure|ps failed|power unit input lost|redundant power supply degraded',
                value_type='str',
            )
        )
        if not power_error_keywords:
            return self.fail(
                '임계치 미정의',
                message='power_error_keywords 가 정의되어 있지 않습니다.',
            )

        rc, out, err = self._ssh(DMESG_POWER_COMMAND)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'SSH 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if rc not in (0, 1):
            return self.fail(
                '점검 명령 실행 실패',
                message='dmesg POWER 로그 점검 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        lines = [line.strip() for line in (out or '').splitlines() if line.strip()]
        matches = self._find_matches(lines, power_error_keywords)
        keyword_counts = self._count_keywords(matches, power_error_keywords)
        threshold_summary = 'power_error_keywords=' + '|'.join(power_error_keywords)

        metrics = {
            'grep_line_count': len(lines),
            'power_error_match_count': len(matches),
            'power_error_keyword_counts': keyword_counts,
            'power_error_matches': matches,
            'grep_lines': lines,
        }
        thresholds = {
            'power_error_keywords': '|'.join(power_error_keywords),
        }

        if matches:
            return self.warn(
                metrics=metrics,
                thresholds=thresholds,
                reasons='전원 장애 관련 키워드가 확인되었습니다. 키워드별 검출 건수: ' + self._format_keyword_counts(keyword_counts),
                message=(
                    '전원 장애 관련 dmesg 로그가 확인되었습니다. '
                    '키워드별 검출 건수: ' + self._format_keyword_counts(keyword_counts) +
                    '. 임계치: ' + threshold_summary
                ),
            )

        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='전원 장애 관련 키워드가 검출되지 않았습니다. 키워드별 검출 건수: ' + self._format_keyword_counts(keyword_counts),
            message=(
                'POWER 로그 점검이 정상 수행되었습니다. '
                '미검출 키워드 현황: ' + self._format_keyword_counts(keyword_counts) +
                '. 임계치: ' + threshold_summary
            ),
        )


CHECK_CLASS = Check
