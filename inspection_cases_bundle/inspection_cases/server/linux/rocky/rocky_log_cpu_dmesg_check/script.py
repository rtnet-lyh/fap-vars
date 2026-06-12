# -*- coding: utf-8 -*-

from .common._base import BaseCheck


DMESG_CPU_COMMAND = "dmesg | grep -i 'ECC error\\|CPU'"


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
        error_keywords = self._split_keywords(
            self.get_threshold_var('error_keywords', default='ecc error|cpu error|offline', value_type='str')
        )
        if not error_keywords:
            return self.fail(
                '임계치 미정의',
                message='error_keywords 가 정의되어 있지 않습니다.',
            )

        rc, out, err = self._ssh(DMESG_CPU_COMMAND)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'SSH 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if rc not in (0, 1):
            return self.fail(
                '점검 명령 실행 실패',
                message='dmesg CPU 로그 점검 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        lines = [line.strip() for line in (out or '').splitlines() if line.strip()]
        matches = self._find_matches(lines, error_keywords)
        keyword_counts = self._count_keywords(matches, error_keywords)
        threshold_summary = 'error_keywords=' + '|'.join(error_keywords)

        metrics = {
            'grep_line_count': len(lines),
            'error_match_count': len(matches),
            'error_keyword_counts': keyword_counts,
            'error_matches': matches,
            'grep_lines': lines,
        }
        thresholds = {
            'error_keywords': '|'.join(error_keywords),
        }

        if matches:
            return self.warn(
                metrics=metrics,
                thresholds=thresholds,
                reasons='CPU 오류 관련 키워드가 확인되었습니다. 키워드별 검출 건수: ' + self._format_keyword_counts(keyword_counts),
                message=(
                    'CPU 오류 관련 dmesg 로그가 확인되었습니다. '
                    '키워드별 검출 건수: ' + self._format_keyword_counts(keyword_counts) +
                    '. 임계치: ' + threshold_summary
                ),
            )

        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='CPU 오류 관련 키워드가 검출되지 않았습니다. 키워드별 검출 건수: ' + self._format_keyword_counts(keyword_counts),
            message=(
                'CPU 로그 점검이 정상 수행되었습니다. '
                '미검출 키워드 현황: ' + self._format_keyword_counts(keyword_counts) +
                '. 임계치: ' + threshold_summary
            ),
        )


CHECK_CLASS = Check
