# type_name

일상점검

# area_name

상태점검

# category_name

server

# application_type

linux

# application

rocky

# inspection_code

U-REPLAY-DMESG-01

# is_required

필수

# inspection_name

시스템 로그

# inspection_content

장치 및 인스턴스가 서비스를 하고 있지만 성능이 저하되거나 손실될 우려 여부 점검

# inspection_command

```bash
dmesg
```

# inspection_output

```text
[    0.000000] Linux version 5.14.0-611.13.1.el9_7.x86_64
[    1.234567] ata1: SATA link up 6.0 Gbps
[    2.345678] EXT4-fs (sda1): mounted filesystem with ordered data mode
[   15.456789] device-mapper: multipath: version 1.14.0 loaded
[  120.567890] Out of memory: Killed process 1234 (java) total-vm:1048576kB
[  180.678901] blk_update_request: I/O error, dev sda, sector 123456
[  181.789012] Buffer I/O error on dev sda1, logical block 15432
[  250.890123] CPU0: Core temperature above threshold, cpu clock throttled
```

# description

- `dmesg` 명령은 시스템 부팅 이후 커널 메시지 버퍼에 기록된 로그를 확인하기 위한 명령이다.
- 본 항목은 시스템, 커널, 메모리, 디스크 I/O, 장치 인식, 드라이버, 파일시스템 관련 로그를 점검하여 장치 및 인스턴스, 서비스 이상 유무를 확인하기 위한 항목이다.
- 특히 `I/O error`, `Buffer I/O error`, `Out of memory`, `Call Trace`, `segfault`, `filesystem error` 와 같은 메시지는 장애 또는 성능 저하의 주요 징후가 될 수 있다.
- 일시적인 정보성 메시지와 실제 오류 메시지를 구분하여 확인해야 하며, 동일 오류가 반복되거나 최근에도 지속적으로 발생하는 경우 원인 분석이 필요하다.
- 커널 로그에서 하드웨어 장애, 메모리 부족, 디스크 오류, 드라이버 이상이 확인되면 관련 장치 점검 및 서비스 영향도 분석을 권고한다.

- **양호**: `dmesg` 출력에서 임계치에 정의된 치명적 오류 키워드가 존재하지 않고, 경고 수준 메시지도 반복적으로 확인되지 않는 상태
- **주의**: 임계치에 정의된 경고 키워드가 존재하거나, 장치/서비스 관련 경고성 로그가 산발적으로 확인되는 상태
- **경고**: 임계치에 정의된 치명적 오류 키워드가 존재하거나, 메모리 부족, 디스크 I/O 오류, 파일시스템 오류, 커널 패닉 관련 로그가 확인되는 상태
- **참고**: 판단기준 적용을 위해 임계치에는 반드시 `critical_log_keywords`, `warning_log_keywords` 와 같이 점검 대상 키워드 목록이 정의되어 있어야 함

# thresholds

[
    {id: null, key: "critical_log_keywords", value: "Out of memory|I/O error|Buffer I/O error|Call Trace|segfault|filesystem error|kernel panic", sortOrder: 0}
,
{id: null, key: "warning_log_keywords", value: "temperature above threshold|cpu clock throttled|throttled|reset|timeout", sortOrder: 1}
]

# inspection_script

# -*- coding: utf-8 -*-

from .common._base import BaseCheck


DMESG_COMMAND = 'dmesg'


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
            line_lower = line.lower()
            matched_keywords = [
                keyword
                for keyword in keywords
                if keyword.lower() in line_lower
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
        critical_keywords = self._split_keywords(
            self.get_threshold_var('critical_log_keywords', default='error|timeout', value_type='str')
        )
        warning_keywords = self._split_keywords(
            self.get_threshold_var('warning_log_keywords', default='warning|out of memory|memory leak|failed|denied', value_type='str')
        )

        ciritical_threshhold = self.get_threshold_var('critical_log_keywords', default='error|timeout', value_type='str')
        warning_threshhold = self.get_threshold_var('warning_log_keywords', default='warning|out of memory|memory leak|failed|denied', value_type='str')

        if not critical_keywords and not warning_keywords:
            return self.fail(
                '임계치 미정의',
                message='critical_log_keywords 또는 warning_log_keywords 가 정의되어 있지 않습니다.',
            )

        rc, out, err = self._ssh(DMESG_COMMAND + f' | grep -E "{ciritical_threshhold}|{warning_threshhold}"')

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'SSH 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if rc != 0:
            return self.fail(
                '점검 명령 실행 실패',
                message='dmesg 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        lines = [line.strip() for line in (out or '').splitlines() if line.strip()]
        if not lines:
            return self.fail(
                '시스템 로그 정보 없음',
                message='dmesg 결과가 비어 있습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        critical_matches = self._find_matches(lines, critical_keywords)
        warning_matches = self._find_matches(lines, warning_keywords)
        critical_keyword_counts = self._count_keywords(critical_matches, critical_keywords)
        warning_keyword_counts = self._count_keywords(warning_matches, warning_keywords)

        metrics = {
            'log_line_count': len(lines),
            'critical_match_count': len(critical_matches),
            'warning_match_count': len(warning_matches),
            'critical_keyword_counts': critical_keyword_counts,
            'warning_keyword_counts': warning_keyword_counts,
            'critical_matches': critical_matches,
            'warning_matches': warning_matches,
        }
        thresholds = {
            'critical_log_keywords': '|'.join(critical_keywords),
            'warning_log_keywords': '|'.join(warning_keywords),
        }
        threshold_summary = (
            'critical_log_keywords=' + thresholds['critical_log_keywords'] +
            '; warning_log_keywords=' + thresholds['warning_log_keywords']
        )

        if critical_matches:
            return self.fail(
                '치명적 커널 로그 감지',
                message=(
                    '치명적 키워드가 포함된 dmesg 로그가 확인되었습니다. '
                    '키워드별 검출 건수: ' + self._format_keyword_counts(critical_keyword_counts) +
                    '. 임계치: ' + threshold_summary
                ),
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        if warning_matches:
            return self.warn(
                metrics=metrics,
                thresholds=thresholds,
                reasons='경고 키워드가 포함된 dmesg 로그가 확인되어 추가 점검이 필요합니다. 키워드별 검출 건수: ' + self._format_keyword_counts(warning_keyword_counts),
                message=(
                    '경고 수준의 dmesg 로그가 확인되었습니다. '
                    '키워드별 검출 건수: ' + self._format_keyword_counts(warning_keyword_counts) +
                    '. 임계치: ' + threshold_summary
                ),
            )

        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons=(
                '치명적 및 경고 키워드가 모두 검출되지 않았습니다. '
                'critical: ' + self._format_keyword_counts(critical_keyword_counts) +
                '; warning: ' + self._format_keyword_counts(warning_keyword_counts)
            ),
            message=(
                'dmesg 시스템 로그 점검이 정상 수행되었습니다. '
                '미검출 키워드 현황 - critical: ' + self._format_keyword_counts(critical_keyword_counts) +
                '; warning: ' + self._format_keyword_counts(warning_keyword_counts) +
                '. 임계치: ' + threshold_summary
            ),
        )


CHECK_CLASS = Check
