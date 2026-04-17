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
            self.get_threshold_var('critical_log_keywords', default='', value_type='str')
        )
        warning_keywords = self._split_keywords(
            self.get_threshold_var('warning_log_keywords', default='', value_type='str')
        )

        if not critical_keywords and not warning_keywords:
            return self.fail(
                '임계치 미정의',
                message='critical_log_keywords 또는 warning_log_keywords 가 정의되어 있지 않습니다.',
            )

        rc, out, err = self._ssh(DMESG_COMMAND)

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
