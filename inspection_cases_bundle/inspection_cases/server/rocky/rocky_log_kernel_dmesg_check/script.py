# -*- coding: utf-8 -*-

from .common._base import BaseCheck


DMESG_PANIC_COMMAND = "dmesg | grep -i 'panic'"


class Check(BaseCheck):
    USE_HOST_CONNECTION = True
    CONNECTION_METHOD = 'ssh'

    def _split_keywords(self, raw_value):
        return [
            token.strip()
            for token in str(raw_value or '').split('|')
            if token.strip()
        ]

    def _count_keywords(self, lines, keywords):
        counts = {keyword: 0 for keyword in keywords}

        for line in lines:
            lowered = line.lower()
            for keyword in keywords:
                if keyword.lower() in lowered:
                    counts[keyword] += 1

        return counts

    def _format_keyword_counts(self, counts):
        return ', '.join(
            f'{keyword}={count}건'
            for keyword, count in counts.items()
        )

    def run(self):
        panic_keywords = self._split_keywords(
            self.get_threshold_var('panic_log_keywords', default='kernel panic|panicking', value_type='str')
        )
        if not panic_keywords:
            return self.fail(
                '임계치 미정의',
                message='panic_log_keywords 가 정의되어 있지 않습니다.',
            )

        rc, out, err = self._ssh(DMESG_PANIC_COMMAND)

        if self._is_connection_error(rc, err):
            return self.fail(
                '호스트 연결 실패',
                message=(err or 'SSH 연결 확인에 실패했습니다.').strip(),
                stderr=(err or '').strip(),
            )

        if rc not in (0, 1):
            return self.fail(
                '점검 명령 실행 실패',
                message='dmesg panic 로그 점검 명령 실행에 실패했습니다.',
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        lines = [line.strip() for line in (out or '').splitlines() if line.strip()]
        keyword_counts = self._count_keywords(lines, panic_keywords)
        threshold_summary = 'panic_log_keywords=' + '|'.join(panic_keywords)

        metrics = {
            'panic_line_count': len(lines),
            'panic_keyword_counts': keyword_counts,
            'panic_lines': lines,
        }
        thresholds = {
            'panic_log_keywords': '|'.join(panic_keywords),
        }

        if lines:
            return self.fail(
                '커널 패닉 로그 감지',
                message=(
                    '커널 패닉 관련 로그가 확인되었습니다. '
                    '키워드별 검출 건수: ' + self._format_keyword_counts(keyword_counts) +
                    '. 임계치: ' + threshold_summary
                ),
                stdout=(out or '').strip(),
                stderr=(err or '').strip(),
            )

        return self.ok(
            metrics=metrics,
            thresholds=thresholds,
            reasons='커널 패닉 관련 키워드가 검출되지 않았습니다. 키워드별 검출 건수: ' + self._format_keyword_counts(keyword_counts),
            message=(
                '커널 패닉 로그 점검이 정상 수행되었습니다. '
                '미검출 키워드 현황: ' + self._format_keyword_counts(keyword_counts) +
                '. 임계치: ' + threshold_summary
            ),
        )


CHECK_CLASS = Check
