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


SV-LIN-RKY-007

# is_required

필수

# inspection_name

MEMORY 로그

# inspection_content

메모리 오류 에러로그 점검(Singlebit/Multibit Errors, Uncorrectable ECC Errors)

# inspection_command

```bash
dmesg | grep -Ei 'ecc error|memory error|single-bit error|multi-bit error'
```

# inspection_output

```text
[   12.345678] EDAC MC0: ECC error detected on CPU#0Channel#1_DIMM#0
[   12.345912] EDAC MC0: Single-bit ECC error corrected on DIMM_A1
[  128.456789] mce: [Hardware Error]: Memory error detected: Uncorrectable ECC error
[  128.457103] EDAC MC0: Multi-bit ECC error detected on DIMM_B2
[  128.457821] EDAC MC0: Uncorrectable ECC error on CPU_SrcID#0_Ha#0_Chan#1_DIMM#1
```

# description

- (ECC 오류 메시지) ECC error detected 메시지가 발견되면, 메모리 모듈에 오류가 발생했음을 나타내며, 메모리 모듈 점검 및 교체 필요
- (단일 비트 오류 메시지) Single-bit ECC error corrected 메시지는 단일 비트 오류가 수정되었음을 나타내며, 이러한 오류가 자주 발생하면 메모리 모듈 점검 권고
- (다중 비트 오류 메시지) Multi-bit ECC error detected 메시지가 발견되면, 다중 비트 오류가 감지되었음을 나타내며, 메모리 모듈 점검 및 교체 필요
- (수정 불가능한 ECC 오류 메시지) Uncorrectable ECC error 메시지가 발견되면, 수정 불가능한 ECC 오류가 발생했음을 나타내며, 메모리 모듈 점검 및 교체 필요

- **양호**: `dmesg | grep -Ei 'ecc error|memory error|single-bit error|multi-bit error'` 결과에 관련 로그가 출력되지 않는 상태
- **경고**: `dmesg | grep -Ei 'ecc error|memory error|single-bit error|multi-bit error'` 결과에 관련 로그가 하나 이상 출력되는 상태
- **참고**: 본 항목은 관련 로그 출력 여부를 기준으로 판단하며, 출력 결과가 존재하면 메모리 오류 징후로 간주함

# thresholds

[
    {id: null, key: "memory_error_keywords", value: "ecc error|memory error|single-bit error|multi-bit error|uncorrectable ecc error", sortOrder: 0}
]

# inspection_script

# -*- coding: utf-8 -*-

from .common._base import BaseCheck


DMESG_MEMORY_COMMAND = "dmesg | grep -Ei 'ecc error|memory error|single-bit error|multi-bit error'"


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
        memory_error_keywords = self._split_keywords(
            self.get_threshold_var(
                'memory_error_keywords',
                default='ecc error|memory error|single-bit error|multi-bit error|uncorrectable ecc error',
                value_type='str',
            )
        )
        if not memory_error_keywords:
            return self.fail(
                '임계치 미정의',
                message='memory_error_keywords 가 정의되어 있지 않습니다.',
            )

        rc, out, err = self._ssh(DMESG_MEMORY_COMMAND)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'SSH 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if rc not in (0, 1):
            return self.fail(
                '점검 명령 실행 실패',
                message='dmesg 메모리 로그 점검 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        lines = [line.strip() for line in (out or '').splitlines() if line.strip()]
        matches = self._find_matches(lines, memory_error_keywords)
        keyword_counts = self._count_keywords(matches, memory_error_keywords)
        threshold_summary = 'memory_error_keywords=' + '|'.join(memory_error_keywords)

        metrics = {
            'grep_line_count': len(lines),
            'memory_error_match_count': len(matches),
            'memory_error_keyword_counts': keyword_counts,
            'memory_error_matches': matches,
            'grep_lines': lines,
        }
        thresholds = {
            'memory_error_keywords': '|'.join(memory_error_keywords),
        }

        if matches:
            return self.warn(
                metrics=metrics,
                thresholds=thresholds,
                reasons='메모리 오류 관련 키워드가 확인되었습니다. 키워드별 검출 건수: ' + self._format_keyword_counts(keyword_counts),
                message=(
                    '메모리 오류 관련 dmesg 로그가 확인되었습니다. '
                    '키워드별 검출 건수: ' + self._format_keyword_counts(keyword_counts) +
                    '. 임계치: ' + threshold_summary
                ),
            )

        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='메모리 오류 관련 키워드가 검출되지 않았습니다. 키워드별 검출 건수: ' + self._format_keyword_counts(keyword_counts),
            message=(
                '메모리 로그 점검이 정상 수행되었습니다. '
                '미검출 키워드 현황: ' + self._format_keyword_counts(keyword_counts) +
                '. 임계치: ' + threshold_summary
            ),
        )


CHECK_CLASS = Check
